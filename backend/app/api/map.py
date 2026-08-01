from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_settled
from app.db.session import get_db
from app.models.user import User
from app.schemas.map import MapResponse, UnlockResponse
from app.services.map_service import get_user_map, unlock_node

router = APIRouter(prefix="/map", tags=["map"])


@router.get("", response_model=MapResponse)
def read_map(
    current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> MapResponse:
    return get_user_map(db, current_user.id)


@router.post("/nodes/{node_key}/unlock", response_model=UnlockResponse)
def unlock(
    node_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnlockResponse:
    unlocked_key, newly_discovered = unlock_node(db, current_user.id, node_key)
    return UnlockResponse(unlocked=unlocked_key, newly_discovered=newly_discovered)
