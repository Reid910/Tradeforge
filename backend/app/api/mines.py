from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.mine import CollectResponse, MineOut, UpgradeResponse
from app.services.mine_service import collect, get_mine, list_mines, upgrade

router = APIRouter(prefix="/mines", tags=["mines"])


@router.get("", response_model=list[MineOut])
def read_mines(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MineOut]:
    return list_mines(db, current_user.id)


@router.get("/{mine_id}", response_model=MineOut)
def read_mine(
    mine_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MineOut:
    return get_mine(db, current_user.id, mine_id)


@router.post("/{mine_id}/collect", response_model=CollectResponse)
def collect_mine(
    mine_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CollectResponse:
    mine, collected, cycles = collect(db, current_user.id, mine_id)
    return CollectResponse(mine=mine, collected=collected, cycles_completed=cycles)


@router.post("/{mine_id}/upgrade", response_model=UpgradeResponse)
def upgrade_mine(
    mine_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UpgradeResponse:
    mine = upgrade(db, current_user.id, mine_id)
    return UpgradeResponse(mine=mine)
