from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ticks import tick_boundary
from app.models.machine import Machine
from app.models.machine_definition import MachineDefinition
from app.schemas.factory import MachineDefinitionOut, MachineInputOut, MachineOut
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
    return MachineOut(id=machine.id, definition=machine_definition_to_out(machine.definition), active=machine.active)


# --- lookups ------------------------------------------------------------


def _get_owned_machine_locked(db: Session, user_id: int, machine_id: int) -> Machine:
    machine = db.execute(
        select(Machine).where(Machine.id == machine_id, Machine.user_id == user_id).with_for_update(of=Machine)
    ).scalar_one_or_none()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine


def list_machine_definitions(db: Session) -> list[MachineDefinitionOut]:
    definitions = db.execute(select(MachineDefinition)).scalars().all()
    return [machine_definition_to_out(d) for d in definitions]


# --- machines ---------------------------------------------------------------


def list_machines(db: Session, user_id: int) -> list[MachineOut]:
    machines = db.execute(select(Machine).where(Machine.user_id == user_id)).scalars().all()
    return [machine_to_out(m) for m in machines]


def create_machine(db: Session, user_id: int, definition_key: str) -> MachineOut:
    definition = db.execute(
        select(MachineDefinition).where(MachineDefinition.key == definition_key)
    ).scalar_one_or_none()
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown machine type")

    machine = Machine(
        user_id=user_id,
        machine_definition_id=definition.id,
        active=True,
        # Snap onto the shared tick grid immediately, same as mines, so
        # this machine is in sync with everything else from the start.
        last_settled_at=tick_boundary(datetime.now(timezone.utc)),
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine_to_out(machine)


def remove_machine(db: Session, user_id: int, machine_id: int) -> None:
    machine = _get_owned_machine_locked(db, user_id, machine_id)
    db.delete(machine)
    db.commit()


def toggle_active(db: Session, user_id: int, machine_id: int) -> MachineOut:
    machine = _get_owned_machine_locked(db, user_id, machine_id)
    machine.active = not machine.active
    if machine.active:
        # Resuming from paused - the clock was frozen while paused, so
        # resume from now rather than counting the whole paused span as
        # available production.
        machine.last_settled_at = tick_boundary(datetime.now(timezone.utc))
    db.commit()
    db.refresh(machine)
    return machine_to_out(machine)


def craft_now(db: Session, user_id: int, machine_id: int) -> MachineOut:
    """Manually run one production cycle immediately, regardless of the
    active/paused state - an on-demand alternative to waiting for the next
    automatic tick.
    """
    machine = _get_owned_machine_locked(db, user_id, machine_id)

    for requirement in machine.definition.inputs:
        if available_quantity(db, user_id, requirement.resource_id) < requirement.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough {requirement.resource.name} to craft",
            )

    for requirement in machine.definition.inputs:
        deduct_inventory(db, user_id, requirement.resource_id, requirement.quantity)

    credit_inventory(db, user_id, machine.definition.output_resource_id, machine.definition.output_amount)

    db.commit()
    db.refresh(machine)
    return machine_to_out(machine)


# --- production settlement -------------------------------------------------


def _settle_machine(db: Session, machine: Machine, now: datetime) -> None:
    max_elapsed = timedelta(hours=settings.max_offline_hours)
    effective_last = max(machine.last_settled_at, now - max_elapsed)

    now_boundary = tick_boundary(now)
    last_boundary = tick_boundary(effective_last)
    if now_boundary <= last_boundary:
        return

    elapsed_ticks = int((now_boundary - last_boundary).total_seconds() // settings.tick_seconds)
    # Always advance the clock once time has genuinely passed, even if
    # starved of input this settle - a starved period is forfeit, not
    # banked, same principle as the mine offline cap. Otherwise restocking
    # after a long gap would trigger an unbounded catch-up burst.
    machine.last_settled_at = now_boundary

    runs = elapsed_ticks
    for requirement in machine.definition.inputs:
        affordable = available_quantity(db, machine.user_id, requirement.resource_id) // requirement.quantity
        runs = min(runs, affordable)

    if runs <= 0:
        return

    for requirement in machine.definition.inputs:
        deduct_inventory(db, machine.user_id, requirement.resource_id, requirement.quantity * runs)

    credit_inventory(db, machine.user_id, machine.definition.output_resource_id, machine.definition.output_amount * runs)


def settle_all_factories(db: Session, user_id: int) -> None:
    """Same lazy, timestamp-based, tick-synchronized pattern as mines - no
    background worker, just settled as a side effect of any request that
    touches factory/inventory data (see api/deps.py). Paused machines are
    skipped entirely (their clock stays frozen).
    """
    machines = (
        db.execute(
            select(Machine).where(Machine.user_id == user_id, Machine.active.is_(True)).with_for_update(of=Machine)
        )
        .scalars()
        .all()
    )
    if not machines:
        return

    now = datetime.now(timezone.utc)
    for machine in machines:
        _settle_machine(db, machine, now)

    db.commit()
