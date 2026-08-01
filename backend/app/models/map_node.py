from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.resource import ResourceDefinition


class MapNode(Base):
    __tablename__ = "map_nodes"
    __table_args__ = (UniqueConstraint("user_id", "node_key", name="uq_map_nodes_user_node_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    node_key: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[int | None] = mapped_column(ForeignKey("resource_definitions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16))  # locked | discovered | unlocked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resource: Mapped[ResourceDefinition | None] = relationship(lazy="joined")
