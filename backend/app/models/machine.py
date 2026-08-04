from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.machine_definition import MachineDefinition


class Machine(Base):
    """An owned machine instance. No position/grid - it's an independent
    unit that pulls its inputs straight from inventory, either
    automatically every tick (while active) or on demand via a manual
    craft. There's no machine-to-machine piping.
    """

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    machine_definition_id: Mapped[int] = mapped_column(ForeignKey("machine_definitions.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tick-boundary-snapped, same shared clock as mines. Frozen while
    # paused - see factory_service.settle_all_factories.
    last_settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    definition: Mapped[MachineDefinition] = relationship(lazy="joined")
