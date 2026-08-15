from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inventory_item import InventoryItem
from app.models.market_order import MarketOrder
from app.models.resource import ResourceDefinition
from app.models.trade import Trade
from app.models.user import User
from app.schemas.market import MarketOrderOut, OrderBookOut, TradeOut
from app.websocket.manager import manager

# --- lookups / locking helpers ----------------------------------------------


def _get_resource(db: Session, resource_key: str) -> ResourceDefinition:
    resource = db.execute(select(ResourceDefinition).where(ResourceDefinition.key == resource_key)).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown resource")
    if not resource.tradable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resource is not tradable")
    return resource


def _get_locked_inventory_item(db: Session, user_id: int, resource_id: int) -> InventoryItem:
    item = db.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user_id, InventoryItem.resource_id == resource_id)
        .with_for_update(of=InventoryItem)
    ).scalar_one_or_none()
    if item is None:
        item = InventoryItem(user_id=user_id, resource_id=resource_id, quantity=0)
        db.add(item)
        db.flush()
    return item


def _get_locked_user(db: Session, user_id: int) -> User:
    return db.execute(select(User).where(User.id == user_id).with_for_update(of=User)).scalar_one()


def _get_locked_order(db: Session, order_id: int) -> MarketOrder:
    return db.execute(select(MarketOrder).where(MarketOrder.id == order_id).with_for_update(of=MarketOrder)).scalar_one()


def _get_owned_open_order_locked(db: Session, user_id: int, order_id: int) -> MarketOrder:
    order = db.execute(
        select(MarketOrder)
        .where(MarketOrder.id == order_id, MarketOrder.user_id == user_id)
        .with_for_update(of=MarketOrder)
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


# --- matching ----------------------------------------------------------------


def _opposite_side_candidates(db: Session, resource_id: int, side: str) -> list[MarketOrder]:
    """Open resting orders on the opposite side, best price first (lowest
    ask for a buy, highest bid for a sell), then earliest created_at -
    standard price-time priority.
    """
    opposite = "sell" if side == "buy" else "buy"
    order_by = MarketOrder.price.asc() if opposite == "sell" else MarketOrder.price.desc()
    return (
        db.execute(
            select(MarketOrder)
            .where(
                MarketOrder.resource_id == resource_id,
                MarketOrder.side == opposite,
                MarketOrder.status == "open",
            )
            .order_by(order_by, MarketOrder.created_at.asc())
        )
        .scalars()
        .all()
    )


def _prices_cross(taker_side: str, taker_price: Decimal, maker_price: Decimal) -> bool:
    return taker_price >= maker_price if taker_side == "buy" else taker_price <= maker_price


def _match_order(db: Session, taker: MarketOrder) -> tuple[list[Trade], dict[int, MarketOrder]]:
    """Match an incoming order against resting opposite-side orders.

    Execution happens at the resting (maker) order's price, never the
    taker's - the taker only ever gets a price at least as good as they
    asked for. A user's own resting orders are skipped (no self-trades):
    matching against yourself would move balance/inventory in a circle
    with no real transfer, and would let a single user manufacture fake
    trade-history/price data.

    Per-fill sequence matches the TODO spec: lock both orders -> confirm
    remaining qty/reserves -> compute fill -> transfer inventory + currency
    -> deduct fee -> update remaining qty -> close filled orders -> write
    trade -> (caller commits, then publishes WS events for what's returned
    here - never before the commit, since Postgres is the source of truth).
    """
    candidates = _opposite_side_candidates(db, taker.resource_id, taker.side)
    trades: list[Trade] = []
    touched_makers: dict[int, MarketOrder] = {}

    for candidate in candidates:
        if taker.remaining_quantity <= 0:
            break
        if candidate.user_id == taker.user_id:
            continue
        if not _prices_cross(taker.side, taker.price, candidate.price):
            break  # book is price-sorted - nothing further down can cross either

        maker = _get_locked_order(db, candidate.id)
        if maker.status != "open" or maker.remaining_quantity <= 0:
            continue

        fill_qty = min(taker.remaining_quantity, maker.remaining_quantity)
        if fill_qty <= 0:
            continue

        fill_price = maker.price
        total_value = fill_price * fill_qty
        fee = (total_value * settings.market_fee_rate).quantize(Decimal("0.0001"))

        buy_order, sell_order = (taker, maker) if taker.side == "buy" else (maker, taker)
        buyer_id, seller_id = buy_order.user_id, sell_order.user_id

        buyer = _get_locked_user(db, buyer_id)
        seller = _get_locked_user(db, seller_id)
        seller_item = _get_locked_inventory_item(db, seller_id, taker.resource_id)
        buyer_item = _get_locked_inventory_item(db, buyer_id, taker.resource_id)

        # Release exactly what was reserved for this fill - reservation was
        # made at the *buy order's own* price (buy_order.price), which can
        # differ from fill_price when the maker offers a better price than
        # the taker bid. Using fill_price here would leave phantom reserved
        # balance behind whenever there's price improvement. The buyer only
        # ever pays total_value (at fill_price), so any improvement is
        # simply freed back to available balance, not charged.
        buyer.reserved_balance -= buy_order.price * fill_qty
        buyer.balance -= total_value
        seller.balance += total_value - fee

        seller_item.reserved_quantity -= fill_qty
        seller_item.quantity -= fill_qty
        buyer_item.quantity += fill_qty

        buy_order.remaining_quantity -= fill_qty
        sell_order.remaining_quantity -= fill_qty
        for order in (buy_order, sell_order):
            if order.remaining_quantity <= 0:
                order.status = "filled"

        trade = Trade(
            resource_id=taker.resource_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            quantity=fill_qty,
            price=fill_price,
            total_value=total_value,
            fee=fee,
        )
        db.add(trade)
        db.flush()
        trades.append(trade)
        touched_makers[maker.id] = maker

    return trades, touched_makers


def _publish_best_prices(db: Session, resource_id: int, resource_key: str) -> None:
    best_bid = db.execute(
        select(MarketOrder.price)
        .where(MarketOrder.resource_id == resource_id, MarketOrder.side == "buy", MarketOrder.status == "open")
        .order_by(MarketOrder.price.desc())
        .limit(1)
    ).scalar_one_or_none()
    best_ask = db.execute(
        select(MarketOrder.price)
        .where(MarketOrder.resource_id == resource_id, MarketOrder.side == "sell", MarketOrder.status == "open")
        .order_by(MarketOrder.price.asc())
        .limit(1)
    ).scalar_one_or_none()
    manager.publish(resource_key, "best_bid_updated", {"price": str(best_bid) if best_bid is not None else None})
    manager.publish(resource_key, "best_ask_updated", {"price": str(best_ask) if best_ask is not None else None})


# --- orders --------------------------------------------------------------


def create_order(
    db: Session, user_id: int, resource_key: str, side: str, price: Decimal, quantity: int
) -> MarketOrderOut:
    resource = _get_resource(db, resource_key)

    if side == "buy":
        user = _get_locked_user(db, user_id)
        cost = price * quantity
        available = user.balance - user.reserved_balance
        if available < cost:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")
        user.reserved_balance += cost
    else:
        item = _get_locked_inventory_item(db, user_id, resource.id)
        available = item.quantity - item.reserved_quantity
        if available < quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient inventory")
        item.reserved_quantity += quantity

    order = MarketOrder(
        user_id=user_id,
        resource_id=resource.id,
        side=side,
        price=price,
        original_quantity=quantity,
        remaining_quantity=quantity,
        status="open",
    )
    db.add(order)
    db.flush()

    trades, touched_makers = _match_order(db, order)

    db.commit()
    db.refresh(order)

    # Publish only after commit - Postgres is the source of truth, and a
    # client must never be told about a fill that isn't durably persisted.
    manager.publish(resource.key, "order_created", MarketOrderOut.model_validate(order).model_dump(mode="json"))
    for maker in touched_makers.values():
        db.refresh(maker)
        manager.publish(resource.key, "order_updated", MarketOrderOut.model_validate(maker).model_dump(mode="json"))
    for trade in trades:
        db.refresh(trade)
        manager.publish(resource.key, "trade_completed", TradeOut.model_validate(trade).model_dump(mode="json"))
    if trades:
        _publish_best_prices(db, resource.id, resource.key)

    return MarketOrderOut.model_validate(order)


def cancel_order(db: Session, user_id: int, order_id: int) -> None:
    order = _get_owned_open_order_locked(db, user_id, order_id)
    if order.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not open")

    if order.side == "buy":
        user = _get_locked_user(db, user_id)
        user.reserved_balance -= order.price * order.remaining_quantity
    else:
        item = _get_locked_inventory_item(db, user_id, order.resource_id)
        item.reserved_quantity -= order.remaining_quantity

    order.status = "cancelled"
    db.commit()
    db.refresh(order)

    resource_key = order.resource.key
    manager.publish(resource_key, "order_cancelled", MarketOrderOut.model_validate(order).model_dump(mode="json"))
    _publish_best_prices(db, order.resource_id, resource_key)


def get_order_book(db: Session, resource_key: str) -> OrderBookOut:
    resource = _get_resource(db, resource_key)
    buy_orders = (
        db.execute(
            select(MarketOrder)
            .where(MarketOrder.resource_id == resource.id, MarketOrder.side == "buy", MarketOrder.status == "open")
            .order_by(MarketOrder.price.desc(), MarketOrder.created_at.asc())
        )
        .scalars()
        .all()
    )
    sell_orders = (
        db.execute(
            select(MarketOrder)
            .where(MarketOrder.resource_id == resource.id, MarketOrder.side == "sell", MarketOrder.status == "open")
            .order_by(MarketOrder.price.asc(), MarketOrder.created_at.asc())
        )
        .scalars()
        .all()
    )
    return OrderBookOut(
        buy_orders=[MarketOrderOut.model_validate(o) for o in buy_orders],
        sell_orders=[MarketOrderOut.model_validate(o) for o in sell_orders],
    )


def list_trades(db: Session, resource_key: str, limit: int = 50) -> list[TradeOut]:
    resource = _get_resource(db, resource_key)
    trades = (
        db.execute(
            select(Trade).where(Trade.resource_id == resource.id).order_by(Trade.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return [TradeOut.model_validate(t) for t in trades]


def list_my_orders(db: Session, user_id: int) -> list[MarketOrderOut]:
    orders = (
        db.execute(select(MarketOrder).where(MarketOrder.user_id == user_id).order_by(MarketOrder.created_at.desc()))
        .scalars()
        .all()
    )
    return [MarketOrderOut.model_validate(o) for o in orders]
