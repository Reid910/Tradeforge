from datetime import datetime

from pydantic import BaseModel

from app.schemas.map import ResourceOut


class InventoryItemOut(BaseModel):
    resource: ResourceOut
    quantity: int
    reserved_quantity: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    items: list[InventoryItemOut]
