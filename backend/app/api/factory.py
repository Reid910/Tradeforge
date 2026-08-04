from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_settled
from app.db.session import get_db
from app.models.user import User
from app.schemas.factory import CreateMachineRequest, MachineDefinitionOut, MachineOut
from app.services.factory_service import (
    craft_now,
    create_machine,
    list_machine_definitions,
    list_machines,
    remove_machine,
    toggle_active,
)

router = APIRouter(prefix="/factory", tags=["factory"])


@router.get("/definitions", response_model=list[MachineDefinitionOut])
def read_machine_definitions(db: Session = Depends(get_db)) -> list[MachineDefinitionOut]:
    return list_machine_definitions(db)


@router.get("/machines", response_model=list[MachineOut])
def read_machines(
    current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> list[MachineOut]:
    return list_machines(db, current_user.id)


@router.post("/machines", response_model=MachineOut, status_code=status.HTTP_201_CREATED)
def create_machine_endpoint(
    payload: CreateMachineRequest,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MachineOut:
    return create_machine(db, current_user.id, payload.machine_definition_key)


@router.delete("/machines/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_machine_endpoint(
    machine_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> None:
    remove_machine(db, current_user.id, machine_id)


@router.post("/machines/{machine_id}/toggle", response_model=MachineOut)
def toggle_machine_endpoint(
    machine_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> MachineOut:
    return toggle_active(db, current_user.id, machine_id)


@router.post("/machines/{machine_id}/craft", response_model=MachineOut)
def craft_now_endpoint(
    machine_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> MachineOut:
    return craft_now(db, current_user.id, machine_id)
