from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MachineChain(Base):
    """A named, ordered production line. Machines are appended left to
    right; each pass, the first machine pulls its inputs from inventory,
    each machine after it sources from the previous machine's output
    where the type matches (else inventory), and only the last machine's
    output is credited back to inventory - see factory_service._run_chain.
    """

    __tablename__ = "machine_chains"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tick-boundary-snapped, same shared clock as mines. Frozen while
    # paused - see factory_service.settle_all_chains.
    last_settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
