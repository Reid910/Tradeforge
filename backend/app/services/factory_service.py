from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ticks import tick_boundary
from app.models.machine import Machine
from app.models.machine_chain import MachineChain
from app.models.machine_definition import MachineDefinition
from app.schemas.factory import MachineChainOut, MachineDefinitionOut, MachineInputOut, MachineOut
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


def _ordered_machines(db: Session, chain_id: int) -> list[Machine]:
    return (
        db.execute(select(Machine).where(Machine.chain_id == chain_id).order_by(Machine.position))
        .scalars()
        .all()
    )


def chain_to_out(db: Session, chain: MachineChain) -> MachineChainOut:
    machines = _ordered_machines(db, chain.id)
    return MachineChainOut(
        id=chain.id,
        name=chain.name,
        active=chain.active,
        machines=[
            MachineOut(id=m.id, definition=machine_definition_to_out(m.definition), position=m.position)
            for m in machines
        ],
    )


# --- lookups ------------------------------------------------------------


def _get_owned_chain_locked(db: Session, user_id: int, chain_id: int) -> MachineChain:
    chain = db.execute(
        select(MachineChain)
        .where(MachineChain.id == chain_id, MachineChain.user_id == user_id)
        .with_for_update(of=MachineChain)
    ).scalar_one_or_none()
    if chain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain not found")
    return chain


def list_machine_definitions(db: Session) -> list[MachineDefinitionOut]:
    definitions = db.execute(select(MachineDefinition)).scalars().all()
    return [machine_definition_to_out(d) for d in definitions]


# --- chains ---------------------------------------------------------------


def list_chains(db: Session, user_id: int) -> list[MachineChainOut]:
    chains = (
        db.execute(select(MachineChain).where(MachineChain.user_id == user_id).order_by(MachineChain.created_at))
        .scalars()
        .all()
    )
    return [chain_to_out(db, c) for c in chains]


def create_chain(db: Session, user_id: int, name: str) -> MachineChainOut:
    chain = MachineChain(
        user_id=user_id,
        name=name,
        active=True,
        # Snap onto the shared tick grid immediately, same as mines, so
        # this chain is in sync with everything else from the start.
        last_settled_at=tick_boundary(datetime.now(timezone.utc)),
    )
    db.add(chain)
    db.commit()
    db.refresh(chain)
    return chain_to_out(db, chain)


def remove_chain(db: Session, user_id: int, chain_id: int) -> None:
    chain = _get_owned_chain_locked(db, user_id, chain_id)
    db.delete(chain)
    db.commit()


def toggle_chain_active(db: Session, user_id: int, chain_id: int) -> MachineChainOut:
    chain = _get_owned_chain_locked(db, user_id, chain_id)
    chain.active = not chain.active
    if chain.active:
        # Resuming from paused - the clock was frozen while paused, so
        # resume from now rather than counting the whole paused span as
        # available production.
        chain.last_settled_at = tick_boundary(datetime.now(timezone.utc))
    db.commit()
    db.refresh(chain)
    return chain_to_out(db, chain)


# --- machines within a chain ------------------------------------------------


def add_machine(db: Session, user_id: int, chain_id: int, definition_key: str) -> MachineChainOut:
    chain = _get_owned_chain_locked(db, user_id, chain_id)

    definition = db.execute(
        select(MachineDefinition).where(MachineDefinition.key == definition_key)
    ).scalar_one_or_none()
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown machine type")

    next_position = len(_ordered_machines(db, chain.id))
    db.add(Machine(chain_id=chain.id, machine_definition_id=definition.id, position=next_position))
    db.commit()
    db.refresh(chain)
    return chain_to_out(db, chain)


def remove_machine(db: Session, user_id: int, chain_id: int, machine_id: int) -> MachineChainOut:
    chain = _get_owned_chain_locked(db, user_id, chain_id)

    machine = db.execute(
        select(Machine).where(Machine.id == machine_id, Machine.chain_id == chain.id)
    ).scalar_one_or_none()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")

    db.delete(machine)
    db.flush()

    # Close the gap so positions stay contiguous (0..n-1) - the settlement
    # walk relies on ordering, not on position values being meaningful.
    for index, remaining in enumerate(_ordered_machines(db, chain.id)):
        remaining.position = index

    db.commit()
    db.refresh(chain)
    return chain_to_out(db, chain)


# --- production settlement -------------------------------------------------


def _chain_inventory_need_per_run(machines: list[Machine]) -> dict[int, int]:
    """Walk the chain once to figure out, for a single pass, how much of
    each resource must come from inventory as opposed to being carried
    from the previous machine's output. Machines run in lockstep with no
    buffering between them, so this per-run breakdown is identical for
    every run - N runs just multiply it out.
    """
    need: dict[int, int] = {}
    carried_resource_id: int | None = None
    carried_amount = 0

    for machine in machines:
        definition = machine.definition
        for requirement in definition.inputs:
            from_carry = requirement.quantity if requirement.resource_id == carried_resource_id else 0
            from_carry = min(from_carry, carried_amount)
            from_inventory = requirement.quantity - from_carry
            if from_inventory > 0:
                need[requirement.resource_id] = need.get(requirement.resource_id, 0) + from_inventory
        carried_resource_id = definition.output_resource_id
        carried_amount = definition.output_amount

    return need


def _run_chain(db: Session, user_id: int, machines: list[Machine], max_runs: int) -> int:
    """Execute up to max_runs passes through the chain. All-or-nothing per
    run: if any machine along the chain can't get enough input, the whole
    pass produces nothing, since only the final machine's output ever
    touches inventory - there's nothing partial to credit.
    """
    if not machines or max_runs <= 0:
        return 0

    need_per_run = _chain_inventory_need_per_run(machines)

    runs = max_runs
    for resource_id, need in need_per_run.items():
        if need <= 0:
            continue
        affordable = available_quantity(db, user_id, resource_id) // need
        runs = min(runs, affordable)

    if runs <= 0:
        return 0

    for resource_id, need in need_per_run.items():
        if need > 0:
            deduct_inventory(db, user_id, resource_id, need * runs)

    tail_definition = machines[-1].definition
    credit_inventory(db, user_id, tail_definition.output_resource_id, tail_definition.output_amount * runs)
    return runs


def run_chain_now(db: Session, user_id: int, chain_id: int) -> MachineChainOut:
    """Manually run one pass through the chain immediately. Only allowed
    while paused, so a manual run can never race with the automatic
    per-tick settlement of the same chain.
    """
    chain = _get_owned_chain_locked(db, user_id, chain_id)
    if chain.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pause the chain before running it manually")

    machines = _ordered_machines(db, chain.id)
    if not machines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add a machine to the chain first")

    runs = _run_chain(db, user_id, machines, max_runs=1)
    if runs == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough resources to run this chain")

    db.commit()
    db.refresh(chain)
    return chain_to_out(db, chain)


def _settle_chain(db: Session, chain: MachineChain, now: datetime) -> None:
    max_elapsed = timedelta(hours=settings.max_offline_hours)
    effective_last = max(chain.last_settled_at, now - max_elapsed)

    now_boundary = tick_boundary(now)
    last_boundary = tick_boundary(effective_last)
    if now_boundary <= last_boundary:
        return

    elapsed_ticks = int((now_boundary - last_boundary).total_seconds() // settings.tick_seconds)
    # Always advance the clock once time has genuinely passed, even if
    # starved of input this settle - a starved period is forfeit, not
    # banked, same principle as the mine offline cap. Otherwise restocking
    # after a long gap would trigger an unbounded catch-up burst.
    chain.last_settled_at = now_boundary

    machines = _ordered_machines(db, chain.id)
    if not machines:
        return

    _run_chain(db, chain.user_id, machines, max_runs=elapsed_ticks)


def settle_all_chains(db: Session, user_id: int) -> None:
    """Same lazy, timestamp-based, tick-synchronized pattern as mines - no
    background worker, just settled as a side effect of any request that
    touches factory/inventory data (see api/deps.py). Paused chains are
    skipped entirely (their clock stays frozen).
    """
    chains = (
        db.execute(
            select(MachineChain)
            .where(MachineChain.user_id == user_id, MachineChain.active.is_(True))
            .with_for_update(of=MachineChain)
        )
        .scalars()
        .all()
    )
    if not chains:
        return

    now = datetime.now(timezone.utc)
    for chain in chains:
        _settle_chain(db, chain, now)

    db.commit()
