from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MachineConnection(Base):
    """Source's output feeds target's input. Each machine can be the source
    of at most one connection and the target of at most one - the two unique
    constraints below enforce that a chain is always a simple line, never a
    branch or merge, entirely at the DB level.
    """

    __tablename__ = "machine_connections"
    __table_args__ = (
        UniqueConstraint("source_machine_id", name="uq_machine_connections_source"),
        UniqueConstraint("target_machine_id", name="uq_machine_connections_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    grid_id: Mapped[int] = mapped_column(ForeignKey("factory_grids.id", ondelete="CASCADE"), index=True)
    source_machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id", ondelete="CASCADE"))
    target_machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
