from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_settled
from app.db.session import get_db
from app.models.user import User
from app.schemas.market import (
    CreateOrderRequest,
    MarketOrderOut,
    OrderBookOut,
    TradeOut,
)
from app.services.market_service import (
    cancel_order,
    create_order,
    get_order_book,
    list_my_orders,
    list_trades,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/resources/{resource_key}/orders", response_model=OrderBookOut)
def read_order_book(resource_key: str, db: Session = Depends(get_db)) -> OrderBookOut:
    return get_order_book(db, resource_key)


@router.get("/resources/{resource_key}/trades", response_model=list[TradeOut])
def read_trades(resource_key: str, db: Session = Depends(get_db)) -> list[TradeOut]:
    return list_trades(db, resource_key)


@router.get("/my-orders", response_model=list[MarketOrderOut])
def read_my_orders(
    current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> list[MarketOrderOut]:
    return list_my_orders(db, current_user.id)


@router.post("/orders", response_model=MarketOrderOut, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user_settled),
    db: Session = Depends(get_db),
) -> MarketOrderOut:
    return create_order(db, current_user.id, payload.resource_key, payload.side, payload.price, payload.quantity)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order_endpoint(
    order_id: int, current_user: User = Depends(get_current_user_settled), db: Session = Depends(get_db)
) -> None:
    cancel_order(db, current_user.id, order_id)
