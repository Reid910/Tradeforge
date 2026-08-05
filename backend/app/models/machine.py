from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.machine_definition import MachineDefinition


class Machine(Base):
    """A machine slot within a chain. Ownership and active/paused state
    live on the parent MachineChain - a machine is just a definition plus
    its position in that chain's left-to-right order.
    """

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    chain_id: Mapped[int] = mapped_column(ForeignKey("machine_chains.id", ondelete="CASCADE"), index=True)
    machine_definition_id: Mapped[int] = mapped_column(ForeignKey("machine_definitions.id"))
    position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    definition: Mapped[MachineDefinition] = relationship(lazy="joined")
