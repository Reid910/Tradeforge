from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ticks import tick_boundary
from app.models.factory_grid import FactoryGrid
from app.models.machine import Machine
from app.models.machine_connection import MachineConnection
from app.models.machine_definition import MachineDefinition
from app.models.resource import ResourceDefinition
from app.schemas.factory import (
    FactoryGridOut,
    MachineConnectionOut,
    MachineDefinitionOut,
    MachineInputOut,
    MachineOut,
)
from app.services.inventory_service import (
    available_quantity,
    credit_inventory,
    deduct_inventory,
)

# --- output shaping ---------------------------------------------------


def machine_definition_to_out(definition: MachineDefinition) -> MachineDefinitionOut:
    return MachineDefinitionOut(
        key=definition.key,
        name=definition.name,
        icon=definition.icon,
        output_resource=definition.output_resource,
        output_amount=definition.output_amount,
        inputs=[MachineInputOut(resource=i.resource, quantity=i.quantity) for i in definition.inputs],
    )


def machine_to_out(machine: Machine) -> MachineOut:
    return MachineOut(
        id=machine.id,
        grid_id=machine.grid_id,
        definition=machine_definition_to_out(machine.definition),
        x=machine.x,
        y=machine.y,
    )


def _grid_to_out(db: Session, grid: FactoryGrid) -> FactoryGridOut:
    machines = db.execute(select(Machine).where(Machine.grid_id == grid.id)).scalars().all()
    connections = db.execute(select(MachineConnection).where(MachineConnection.grid_id == grid.id)).scalars().all()
    return FactoryGridOut(
        id=grid.id,
        slot_index=grid.slot_index,
        width=grid.width,
        height=grid.height,
        machines=[machine_to_out(m) for m in machines],
        connections=[
            MachineConnectionOut(id=c.id, source_machine_id=c.source_machine_id, target_machine_id=c.target_machine_id)
            for c in connections
        ],
    )


# --- lookups ------------------------------------------------------------


def _get_owned_grid(db: Session, user_id: int, grid_id: int) -> FactoryGrid:
    grid = db.execute(
        select(FactoryGrid).where(FactoryGrid.id == grid_id, FactoryGrid.user_id == user_id)
    ).scalar_one_or_none()
    if grid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grid not found")
    return grid


def _get_owned_machine(db: Session, user_id: int, machine_id: int) -> Machine:
    machine = db.execute(
        select(Machine).where(Machine.id == machine_id, Machine.user_id == user_id)
    ).scalar_one_or_none()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine


def list_machine_definitions(db: Session) -> list[MachineDefinitionOut]:
    definitions = db.execute(select(MachineDefinition)).scalars().all()
    return [machine_definition_to_out(d) for d in definitions]


# --- grids ----------------------------------------------------------------


def seed_first_grid(db: Session, user_id: int) -> None:
    db.add(
        FactoryGrid(
            user_id=user_id,
            slot_index=1,
            width=settings.factory_grid_width,
            height=settings.factory_grid_height,
            # Snap onto the shared tick grid immediately, same as mines, so
            # this grid is in sync with everything else from the start.
            last_settled_at=tick_boundary(datetime.now(timezone.utc)),
        )
    )
    db.commit()


def list_grids(db: Session, user_id: int) -> list[FactoryGridOut]:
    grids = (
        db.execute(select(FactoryGrid).where(FactoryGrid.user_id == user_id).order_by(FactoryGrid.slot_index))
        .scalars()
        .all()
    )
    return [_grid_to_out(db, g) for g in grids]


def unlock_grid(db: Session, user_id: int) -> FactoryGridOut:
    existing = db.execute(select(FactoryGrid).where(FactoryGrid.user_id == user_id)).scalars().all()
    next_slot = len(existing) + 1

    cost_resource_id = db.scalar(
        select(ResourceDefinition.id).where(ResourceDefinition.key == settings.factory_grid_unlock_cost_resource_key)
    )
    cost_amount = settings.factory_grid_unlock_cost_amount

    if available_quantity(db, user_id, cost_resource_id) < cost_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough {settings.factory_grid_unlock_cost_resource_key} to unlock a new grid (need {cost_amount})",
        )

    deduct_inventory(db, user_id, cost_resource_id, cost_amount)

    grid = FactoryGrid(
        user_id=user_id,
        slot_index=next_slot,
        width=settings.factory_grid_width,
        height=settings.factory_grid_height,
        last_settled_at=tick_boundary(datetime.now(timezone.utc)),
    )
    db.add(grid)
    db.commit()
    db.refresh(grid)
    return _grid_to_out(db, grid)


# --- machines ---------------------------------------------------------------


def place_machine(db: Session, user_id: int, grid_id: int, definition_key: str, x: int, y: int) -> MachineOut:
    grid = _get_owned_grid(db, user_id, grid_id)

    if not (0 <= x < grid.width and 0 <= y < grid.height):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position is outside the grid")

    occupied = db.execute(
        select(Machine).where(Machine.grid_id == grid_id, Machine.x == x, Machine.y == y)
    ).scalar_one_or_none()
    if occupied is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That cell is already occupied")

    definition = db.execute(
        select(MachineDefinition).where(MachineDefinition.key == definition_key)
    ).scalar_one_or_none()
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown machine type")

    machine = Machine(user_id=user_id, grid_id=grid_id, machine_definition_id=definition.id, x=x, y=y)
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine_to_out(machine)


def remove_machine(db: Session, user_id: int, machine_id: int) -> None:
    machine = _get_owned_machine(db, user_id, machine_id)
    db.delete(machine)
    db.commit()


# --- connections --------------------------------------------------------


def _would_create_cycle(db: Session, grid_id: int, source_id: int, target_id: int) -> bool:
    connections = db.execute(select(MachineConnection).where(MachineConnection.grid_id == grid_id)).scalars().all()
    next_by_source = {c.source_machine_id: c.target_machine_id for c in connections}

    current = target_id
    seen: set[int] = set()
    while current in next_by_source and current not in seen:
        seen.add(current)
        current = next_by_source[current]
        if current == source_id:
            return True
    return False


def connect_machines(db: Session, user_id: int, source_machine_id: int, target_machine_id: int) -> MachineConnectionOut:
    if source_machine_id == target_machine_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A machine can't connect to itself")

    source = _get_owned_machine(db, user_id, source_machine_id)
    target = _get_owned_machine(db, user_id, target_machine_id)

    if source.grid_id != target.grid_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Machines must be on the same grid")

    existing_out = db.execute(
        select(MachineConnection).where(MachineConnection.source_machine_id == source_machine_id)
    ).scalar_one_or_none()
    if existing_out is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That machine already has an outgoing connection")

    existing_in = db.execute(
        select(MachineConnection).where(MachineConnection.target_machine_id == target_machine_id)
    ).scalar_one_or_none()
    if existing_in is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That machine already has an incoming connection")

    if _would_create_cycle(db, source.grid_id, source_machine_id, target_machine_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That connection would create a cycle")

    connection = MachineConnection(
        grid_id=source.grid_id, source_machine_id=source_machine_id, target_machine_id=target_machine_id
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return MachineConnectionOut(
        id=connection.id, source_machine_id=connection.source_machine_id, target_machine_id=connection.target_machine_id
    )


def disconnect_machines(db: Session, user_id: int, connection_id: int) -> None:
    connection = db.execute(
        select(MachineConnection)
        .join(Machine, Machine.id == MachineConnection.source_machine_id)
        .where(MachineConnection.id == connection_id, Machine.user_id == user_id)
    ).scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    db.delete(connection)
    db.commit()


# --- production settlement -------------------------------------------------


def _build_chains(machines: list[Machine], connections: list[MachineConnection]) -> list[list[Machine]]:
    """Every machine with no incoming connection is a chain head; walk
    forward via outgoing connections to build the ordered chain. Machines
    that are part of a cycle never qualify as a head (connect_machines
    rejects cycles at creation time, so this should never actually occur),
    and simply produce nothing.
    """
    machines_by_id = {m.id: m for m in machines}
    next_by_source = {c.source_machine_id: c.target_machine_id for c in connections}
    has_incoming = {c.target_machine_id for c in connections}

    chains = []
    for machine in machines:
        if machine.id in has_incoming:
            continue
        chain = [machine]
        current_id = machine.id
        while current_id in next_by_source:
            current_id = next_by_source[current_id]
            chain.append(machines_by_id[current_id])
        chains.append(chain)
    return chains


def _settle_grid(db: Session, grid: FactoryGrid, now: datetime) -> None:
    max_elapsed = timedelta(hours=settings.max_offline_hours)
    effective_last = max(grid.last_settled_at, now - max_elapsed)

    now_boundary = tick_boundary(now)
    last_boundary = tick_boundary(effective_last)
    if now_boundary <= last_boundary:
        return

    elapsed_ticks = int((now_boundary - last_boundary).total_seconds() // settings.tick_seconds)
    # Always advance the clock once time has genuinely passed, even if a
    # chain ends up producing nothing this settle (input-starved) - a
    # starved period is forfeit, not banked, same principle as the mine
    # offline cap. Otherwise restocking after a long gap would trigger an
    # unbounded catch-up burst instead of a capped one.
    grid.last_settled_at = now_boundary

    machines = db.execute(select(Machine).where(Machine.grid_id == grid.id)).scalars().all()
    if not machines:
        return
    connections = db.execute(select(MachineConnection).where(MachineConnection.grid_id == grid.id)).scalars().all()

    for chain in _build_chains(machines, connections):
        head, tail = chain[0], chain[-1]
        head_inputs = head.definition.inputs

        runs = elapsed_ticks
        for requirement in head_inputs:
            affordable = available_quantity(db, grid.user_id, requirement.resource_id) // requirement.quantity
            runs = min(runs, affordable)

        if runs <= 0:
            continue

        for requirement in head_inputs:
            deduct_inventory(db, grid.user_id, requirement.resource_id, requirement.quantity * runs)

        credit_inventory(db, grid.user_id, tail.definition.output_resource_id, tail.definition.output_amount * runs)


def settle_all_factories(db: Session, user_id: int) -> None:
    """Same lazy, timestamp-based, tick-synchronized pattern as mines - no
    background worker, just settled as a side effect of any request that
    touches factory/inventory data (see api/deps.py).
    """
    grids = (
        db.execute(select(FactoryGrid).where(FactoryGrid.user_id == user_id).with_for_update(of=FactoryGrid))
        .scalars()
        .all()
    )
    if not grids:
        return

    now = datetime.now(timezone.utc)
    for grid in grids:
        _settle_grid(db, grid, now)

    db.commit()
