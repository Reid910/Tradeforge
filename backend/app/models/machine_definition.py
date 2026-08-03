from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.resource import ResourceDefinition


class MachineDefinition(Base):
    __tablename__ = "machine_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    icon: Mapped[str] = mapped_column(String(8))
    output_resource_id: Mapped[int] = mapped_column(ForeignKey("resource_definitions.id"))
    output_amount: Mapped[int] = mapped_column(Integer, default=1)

    output_resource: Mapped[ResourceDefinition] = relationship(lazy="joined")
    # selectin, not joined - joined eager loading against a *collection*
    # duplicates the parent row per child and requires callers to remember
    # Result.unique(); selectin issues a separate query and avoids that trap.
    inputs: Mapped[list["MachineDefinitionInput"]] = relationship(lazy="selectin")


class MachineDefinitionInput(Base):
    __tablename__ = "machine_definition_inputs"
    __table_args__ = (
        UniqueConstraint("machine_definition_id", "resource_id", name="uq_machine_definition_inputs"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_definition_id: Mapped[int] = mapped_column(
        ForeignKey("machine_definitions.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[int] = mapped_column(ForeignKey("resource_definitions.id"))
    quantity: Mapped[int] = mapped_column(Integer)

    resource: Mapped[ResourceDefinition] = relationship(lazy="joined")
