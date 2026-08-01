from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResourceDefinition(Base):
    __tablename__ = "resource_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))  # raw | intermediate | finished | rare
    icon: Mapped[str] = mapped_column(String(8))
    base_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    yield_amount: Mapped[int] = mapped_column(default=1)
    rarity: Mapped[str] = mapped_column(String(16), default="common")
    tradable: Mapped[bool] = mapped_column(Boolean, default=True)
