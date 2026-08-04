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
    active: bool


class CreateMachineRequest(BaseModel):
    machine_definition_key: str
