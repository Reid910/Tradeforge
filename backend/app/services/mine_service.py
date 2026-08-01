from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.mine import Mine
from app.schemas.mine import MineOut
from app.services.inventory_service import credit_inventory


def cycle_seconds_for_level(level: int) -> int:
    reduced = settings.mine_base_cycle_seconds - (level - 1) * settings.mine_cycle_reduction_per_level
    return max(reduced, settings.mine_min_cycle_seconds)


def storage_capacity_for_level(level: int) -> int:
    return settings.mine_base_storage + (level - 1) * settings.mine_storage_per_level


def create_mine(db: Session, user_id: int, map_node_id: int, resource_id: int) -> Mine:
    mine = Mine(
        user_id=user_id,
        map_node_id=map_node_id,
        resource_id=resource_id,
        level=1,
        storage_capacity=storage_capacity_for_level(1),
        stored_quantity=0,
    )
    db.add(mine)
    db.flush()
    return mine


def mine_to_out(mine: Mine) -> MineOut:
    return MineOut(
        id=mine.id,
        map_node_id=mine.map_node_id,
        resource=mine.resource,
        level=mine.level,
        storage_capacity=mine.storage_capacity,
        stored_quantity=mine.stored_quantity,
        cycle_seconds=cycle_seconds_for_level(mine.level),
        last_collected_at=mine.last_collected_at,
    )


def _get_owned_mine_locked(db: Session, user_id: int, mine_id: int) -> Mine:
    mine = db.execute(
        select(Mine).where(Mine.id == mine_id, Mine.user_id == user_id).with_for_update(of=Mine)
    ).scalar_one_or_none()
    if mine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mine not found")
    return mine


def _completed_cycles(mine: Mine, now: datetime) -> int:
    """Elapsed time since last collection, capped against offline farming, in whole cycles."""
    elapsed = now - mine.last_collected_at
    max_elapsed = timedelta(hours=settings.mine_max_offline_hours)
    elapsed = min(elapsed, max_elapsed)
    if elapsed <= timedelta(0):
        return 0
    return int(elapsed.total_seconds() // cycle_seconds_for_level(mine.level))


def get_mine(db: Session, user_id: int, mine_id: int) -> MineOut:
    mine = db.execute(select(Mine).where(Mine.id == mine_id, Mine.user_id == user_id)).scalar_one_or_none()
    if mine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mine not found")
    return mine_to_out(mine)


def list_mines(db: Session, user_id: int) -> list[MineOut]:
    mines = db.execute(select(Mine).where(Mine.user_id == user_id)).scalars().all()
    return [mine_to_out(m) for m in mines]


def collect(db: Session, user_id: int, mine_id: int) -> tuple[MineOut, int, int]:
    """Bank newly completed cycles (capped at storage), then move everything
    banked into the player's inventory. Idempotent: calling this again
    immediately afterward produces zero new cycles and collects nothing.
    """
    mine = _get_owned_mine_locked(db, user_id, mine_id)
    now = datetime.now(timezone.utc)

    cycles = _completed_cycles(mine, now)
    if cycles > 0:
        produced = cycles * mine.resource.yield_amount
        mine.stored_quantity = min(mine.stored_quantity + produced, mine.storage_capacity)
        mine.last_collected_at = mine.last_collected_at + timedelta(seconds=cycles * cycle_seconds_for_level(mine.level))

    collected = mine.stored_quantity
    if collected > 0:
        credit_inventory(db, user_id, mine.resource_id, collected)
        mine.stored_quantity = 0

    db.commit()
    db.refresh(mine)
    return mine_to_out(mine), collected, cycles


def upgrade(db: Session, user_id: int, mine_id: int) -> MineOut:
    mine = _get_owned_mine_locked(db, user_id, mine_id)

    if mine.level >= settings.mine_max_level:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mine is already at max level")

    # Free for now - there's no currency sink yet since the market doesn't
    # exist. Wire in a balance check + deduction here once it does.
    mine.level += 1
    mine.storage_capacity = storage_capacity_for_level(mine.level)

    db.commit()
    db.refresh(mine)
    return mine_to_out(mine)
