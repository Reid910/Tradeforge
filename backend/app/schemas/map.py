from decimal import Decimal

from pydantic import BaseModel


class ResourceOut(BaseModel):
    key: str
    name: str
    icon: str
    category: str
    rarity: str
    yield_amount: int
    base_value: Decimal

    model_config = {"from_attributes": True}


class MapNodeOut(BaseModel):
    node_key: str
    status: str
    resource: ResourceOut | None


class MapEdgeOut(BaseModel):
    source: str
    target: str


class MapResponse(BaseModel):
    nodes: list[MapNodeOut]
    edges: list[MapEdgeOut]


class UnlockResponse(BaseModel):
    unlocked: str
    newly_discovered: list[str]
