from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory_item import InventoryItem
from app.schemas.inventory import InventoryItemOut


def _get_or_create_locked(db: Session, user_id: int, resource_id: int) -> InventoryItem:
    """Caller is responsible for the surrounding transaction/commit."""
    item = db.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user_id, InventoryItem.resource_id == resource_id)
        .with_for_update(of=InventoryItem)
    ).scalar_one_or_none()

    if item is None:
        item = InventoryItem(user_id=user_id, resource_id=resource_id, quantity=0)
        db.add(item)
        db.flush()

    return item


def credit_inventory(db: Session, user_id: int, resource_id: int, amount: int) -> InventoryItem:
    item = _get_or_create_locked(db, user_id, resource_id)
    item.quantity += amount
    db.flush()
    return item


def deduct_inventory(db: Session, user_id: int, resource_id: int, amount: int) -> InventoryItem:
    """Caller must ensure amount <= available quantity - this floors at 0
    rather than validating, since callers (factory settlement) compute the
    affordable amount themselves before calling.
    """
    item = _get_or_create_locked(db, user_id, resource_id)
    item.quantity = max(item.quantity - amount, 0)
    db.flush()
    return item


def available_quantity(db: Session, user_id: int, resource_id: int) -> int:
    return _get_or_create_locked(db, user_id, resource_id).quantity


def list_inventory(db: Session, user_id: int) -> list[InventoryItemOut]:
    items = db.execute(select(InventoryItem).where(InventoryItem.user_id == user_id)).scalars().all()
    return [InventoryItemOut.model_validate(i) for i in items]
