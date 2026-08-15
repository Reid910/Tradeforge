from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.resource import ResourceDefinition


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resource_definitions.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    buy_order_id: Mapped[int] = mapped_column(ForeignKey("market_orders.id", ondelete="CASCADE"))
    sell_order_id: Mapped[int] = mapped_column(ForeignKey("market_orders.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    resource: Mapped[ResourceDefinition] = relationship(lazy="joined")
