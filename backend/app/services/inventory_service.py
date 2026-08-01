from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory_item import InventoryItem
from app.schemas.inventory import InventoryItemOut


def credit_inventory(db: Session, user_id: int, resource_id: int, amount: int) -> InventoryItem:
    """Caller is responsible for the surrounding transaction/commit."""
    item = db.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user_id, InventoryItem.resource_id == resource_id)
        .with_for_update(of=InventoryItem)
    ).scalar_one_or_none()

    if item is None:
        item = InventoryItem(user_id=user_id, resource_id=resource_id, quantity=amount)
        db.add(item)
    else:
        item.quantity += amount

    db.flush()
    return item


def list_inventory(db: Session, user_id: int) -> list[InventoryItemOut]:
    items = db.execute(select(InventoryItem).where(InventoryItem.user_id == user_id)).scalars().all()
    return [InventoryItemOut.model_validate(i) for i in items]
