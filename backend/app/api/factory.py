from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_settled
from app.db.session import get_db
from app.models.user import User
from app.schemas.factory import AddMachineRequest, CreateChainRequest, MachineChainOut, MachineDefinitionOut
from app.services.factory_service import (
    add_machine,
    create_chain,
    list_chains,
    list_machine_definitions,
    remove_chain,
    remove_machine,
    run_chain_now,
    toggle_chain_active,
)

router = APIRouter(prefix="/factory", tags=["factory"])


@router.get("/definitions", response_model=list[MachineDefinitionOut])
def read_machine_definitions(db: Session = Depends(get_db)) -> list[MachineDefinitionOut]:
    return list_machine_definitions(db)


@router.get("/chains", response_model=list[MachineChainOut])
def read_chains(
    current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> list[MachineChainOut]:
    return list_chains(db, current_user.id)


@router.post("/chains", response_model=MachineChainOut, status_code=status.HTTP_201_CREATED)
def create_chain_endpoint(
    payload: CreateChainRequest,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MachineChainOut:
    return create_chain(db, current_user.id, payload.name)


@router.delete("/chains/{chain_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chain_endpoint(
    chain_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> None:
    remove_chain(db, current_user.id, chain_id)


@router.post("/chains/{chain_id}/toggle", response_model=MachineChainOut)
def toggle_chain_endpoint(
    chain_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> MachineChainOut:
    return toggle_chain_active(db, current_user.id, chain_id)


@router.post("/chains/{chain_id}/run", response_model=MachineChainOut)
def run_chain_endpoint(
    chain_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> MachineChainOut:
    return run_chain_now(db, current_user.id, chain_id)


@router.post("/chains/{chain_id}/machines", response_model=MachineChainOut, status_code=status.HTTP_201_CREATED)
def add_machine_endpoint(
    chain_id: int,
    payload: AddMachineRequest,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MachineChainOut:
    return add_machine(db, current_user.id, chain_id, payload.machine_definition_key)


@router.delete("/chains/{chain_id}/machines/{machine_id}", response_model=MachineChainOut)
def remove_machine_endpoint(
    chain_id: int,
    machine_id: int,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MachineChainOut:
    return remove_machine(db, current_user.id, chain_id, machine_id)
