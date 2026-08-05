from pydantic import BaseModel

from app.schemas.map import ResourceOut


class MachineInputOut(BaseModel):
    resource: ResourceOut
    quantity: int


class MachineDefinitionOut(BaseModel):
    key: str
    name: str
    icon: str
    output_resource: ResourceOut
    output_amount: int
    inputs: list[MachineInputOut]


class MachineOut(BaseModel):
    id: int
    definition: MachineDefinitionOut
    position: int


class MachineChainOut(BaseModel):
    id: int
    name: str
    active: bool
    machines: list[MachineOut]


class CreateChainRequest(BaseModel):
    name: str


class AddMachineRequest(BaseModel):
    machine_definition_key: str
