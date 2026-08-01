from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.resource import ResourceDefinition


class Mine(Base):
    __tablename__ = "mines"
    __table_args__ = (UniqueConstraint("map_node_id", name="uq_mines_map_node_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    map_node_id: Mapped[int] = mapped_column(ForeignKey("map_nodes.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resource_definitions.id"))
    level: Mapped[int] = mapped_column(Integer, default=1)
    storage_capacity: Mapped[int] = mapped_column(Integer)
    stored_quantity: Mapped[int] = mapped_column(Integer, default=0)
    last_collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resource: Mapped[ResourceDefinition] = relationship(lazy="joined")
