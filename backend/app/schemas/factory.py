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
    grid_id: int
    definition: MachineDefinitionOut
    x: int
    y: int


class MachineConnectionOut(BaseModel):
    id: int
    source_machine_id: int
    target_machine_id: int


class FactoryGridOut(BaseModel):
    id: int
    slot_index: int
    width: int
    height: int
    machines: list[MachineOut]
    connections: list[MachineConnectionOut]


class PlaceMachineRequest(BaseModel):
    machine_definition_key: str
    x: int
    y: int


class ConnectRequest(BaseModel):
    source_machine_id: int
    target_machine_id: int


class UnlockGridResponse(BaseModel):
    grid: FactoryGridOut
