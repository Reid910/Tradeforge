from datetime import datetime

from pydantic import BaseModel

from app.schemas.map import ResourceOut


class MineOut(BaseModel):
    id: int
    map_node_id: int
    resource: ResourceOut
    level: int
    storage_capacity: int
    stored_quantity: int
    cycle_seconds: int
    last_collected_at: datetime

    model_config = {"from_attributes": True}


class UpgradeResponse(BaseModel):
    mine: MineOut
