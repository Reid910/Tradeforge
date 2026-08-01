from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.mine import Mine
from app.schemas.mine import MineOut
from app.services.inventory_service import credit_inventory


def _tick_boundary(dt: datetime) -> datetime:
    """Floor a timestamp down to the shared global tick grid. Every mine
    settles against this same grid (not its own private clock), so
    production across all mines stays in lockstep instead of drifting out
    of phase with each other based on when each was created.
    """
    epoch_seconds = dt.timestamp()
    floored = (epoch_seconds // settings.mine_tick_seconds) * settings.mine_tick_seconds
    return datetime.fromtimestamp(floored, tz=timezone.utc)


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
        # Snap onto the shared tick grid immediately so this mine is in sync
        # with every other mine from the moment it's created.
        last_collected_at=_tick_boundary(datetime.now(timezone.utc)),
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
        cycle_seconds=settings.mine_tick_seconds,
        last_collected_at=mine.last_collected_at,
    )


def _get_owned_mine_locked(db: Session, user_id: int, mine_id: int) -> Mine:
    mine = db.execute(
        select(Mine).where(Mine.id == mine_id, Mine.user_id == user_id).with_for_update(of=Mine)
    ).scalar_one_or_none()
    if mine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mine not found")
    return mine


def _completed_ticks(mine: Mine, now: datetime) -> int:
    """Whole shared ticks passed since this mine's last settle, capped
    against offline farming.
    """
    max_elapsed = timedelta(hours=settings.mine_max_offline_hours)
    effective_last = max(mine.last_collected_at, now - max_elapsed)

    now_boundary = _tick_boundary(now)
    last_boundary = _tick_boundary(effective_last)
    if now_boundary <= last_boundary:
        return 0
    return int((now_boundary - last_boundary).total_seconds() // settings.mine_tick_seconds)


def _settle(db: Session, mine: Mine, now: datetime) -> int:
    """Bank newly completed ticks (storage-capped), then move everything
    banked straight into the player's inventory. No-op (returns 0) if no
    tick has completed since the last settle - callers control commit.
    """
    ticks = _completed_ticks(mine, now)
    if ticks > 0:
        produced = ticks * mine.resource.yield_amount * mine.level
        mine.stored_quantity = min(mine.stored_quantity + produced, mine.storage_capacity)
        mine.last_collected_at = _tick_boundary(now)

    banked = mine.stored_quantity
    if banked > 0:
        credit_inventory(db, mine.user_id, mine.resource_id, banked)
        mine.stored_quantity = 0

    return banked


def settle_all_mines(db: Session, user_id: int) -> None:
    """Auto-credit inventory for every mine the user owns. There's no
    player-facing "collect" action - production is meant to pile up on its
    own, so this runs as a side effect of any request that touches mines,
    map, or inventory (see api/deps.py) rather than a dedicated endpoint.
    Still no permanent background loop: purely lazy, timestamp-based math,
    with every mine settled against the same `now` so they stay in sync.
    """
    mines = db.execute(select(Mine).where(Mine.user_id == user_id).with_for_update(of=Mine)).scalars().all()
    if not mines:
        return

    now = datetime.now(timezone.utc)
    for mine in mines:
        _settle(db, mine, now)

    db.commit()


def get_mine(db: Session, user_id: int, mine_id: int) -> MineOut:
    mine = db.execute(select(Mine).where(Mine.id == mine_id, Mine.user_id == user_id)).scalar_one_or_none()
    if mine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mine not found")
    return mine_to_out(mine)


def list_mines(db: Session, user_id: int) -> list[MineOut]:
    mines = db.execute(select(Mine).where(Mine.user_id == user_id)).scalars().all()
    return [mine_to_out(m) for m in mines]


def upgrade(db: Session, user_id: int, mine_id: int) -> MineOut:
    mine = _get_owned_mine_locked(db, user_id, mine_id)

    if mine.level >= settings.mine_max_level:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mine is already at max level")

    # Free for now - there's no currency sink yet since the market doesn't
    # exist. Wire in a balance check + deduction here once it does. Level
    # increases output-per-tick and storage - never tick speed, so mines
    # stay in sync with each other regardless of level.
    mine.level += 1
    mine.storage_capacity = storage_capacity_for_level(mine.level)

    db.commit()
    db.refresh(mine)
    return mine_to_out(mine)
