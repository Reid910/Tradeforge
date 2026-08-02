from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_settled
from app.db.session import get_db
from app.models.user import User
from app.schemas.factory import (
    ConnectRequest,
    FactoryGridOut,
    MachineConnectionOut,
    MachineDefinitionOut,
    MachineOut,
    PlaceMachineRequest,
)
from app.services.factory_service import (
    connect_machines,
    disconnect_machines,
    list_grids,
    list_machine_definitions,
    place_machine,
    remove_machine,
    unlock_grid,
)

router = APIRouter(prefix="/factory", tags=["factory"])


@router.get("/definitions", response_model=list[MachineDefinitionOut])
def read_machine_definitions(db: Session = Depends(get_db)) -> list[MachineDefinitionOut]:
    return list_machine_definitions(db)


@router.get("/grids", response_model=list[FactoryGridOut])
def read_grids(
    current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> list[FactoryGridOut]:
    return list_grids(db, current_user.id)


@router.post("/grids/unlock", response_model=FactoryGridOut, status_code=status.HTTP_201_CREATED)
def unlock_new_grid(
    current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> FactoryGridOut:
    return unlock_grid(db, current_user.id)


@router.post("/grids/{grid_id}/machines", response_model=MachineOut, status_code=status.HTTP_201_CREATED)
def place_machine_endpoint(
    grid_id: int,
    payload: PlaceMachineRequest,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MachineOut:
    return place_machine(db, current_user.id, grid_id, payload.machine_definition_key, payload.x, payload.y)


@router.delete("/machines/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_machine_endpoint(
    machine_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> None:
    remove_machine(db, current_user.id, machine_id)


@router.post("/connections", response_model=MachineConnectionOut, status_code=status.HTTP_201_CREATED)
def connect_machines_endpoint(
    payload: ConnectRequest,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MachineConnectionOut:
    return connect_machines(db, current_user.id, payload.source_machine_id, payload.target_machine_id)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_machines_endpoint(
    connection_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> None:
    disconnect_machines(db, current_user.id, connection_id)
