from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.machine_definition import MachineDefinition


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    grid_id: Mapped[int] = mapped_column(ForeignKey("factory_grids.id", ondelete="CASCADE"), index=True)
    machine_definition_id: Mapped[int] = mapped_column(ForeignKey("machine_definitions.id"))
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    definition: Mapped[MachineDefinition] = relationship(lazy="joined")
