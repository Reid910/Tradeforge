from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.inventory import InventoryResponse
from app.services.inventory_service import list_inventory

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=InventoryResponse)
def read_inventory(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> InventoryResponse:
    return InventoryResponse(items=list_inventory(db, current_user.id))
