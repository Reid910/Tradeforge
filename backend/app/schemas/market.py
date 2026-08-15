from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.map import ResourceOut


class CreateOrderRequest(BaseModel):
    resource_key: str
    side: str = Field(pattern="^(buy|sell)$")
    price: Decimal = Field(gt=0)
    quantity: int = Field(gt=0)


class MarketOrderOut(BaseModel):
    id: int
    resource: ResourceOut
    side: str
    price: Decimal
    original_quantity: int
    remaining_quantity: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeOut(BaseModel):
    id: int
    resource: ResourceOut
    quantity: int
    price: Decimal
    total_value: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderBookOut(BaseModel):
    buy_orders: list[MarketOrderOut]
    sell_orders: list[MarketOrderOut]
