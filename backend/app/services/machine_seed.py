from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.machine_definition import MachineDefinition, MachineDefinitionInput
from app.models.resource import ResourceDefinition

MACHINE_SEED = [
    dict(
        key="furnace",
        name="Furnace",
        icon="🔥",
        output_key="copper_ingot",
        output_amount=1,
        inputs=[("copper_ore", 1), ("coal", 1)],
    ),
    dict(
        key="press",
        name="Press",
        icon="🛠",
        output_key="copper_plate",
        output_amount=1,
        # Machines in a chain run in lockstep (no buffering between them),
        # so this must be <= the upstream Furnace's 1x output per run, or
        # the chain could never produce anything.
        inputs=[("copper_ingot", 1)],
    ),
    dict(
        key="smelter",
        name="Smelter",
        icon="🔥",
        output_key="steel",
        output_amount=1,
        inputs=[("iron_ore", 1), ("coal", 1)],
    ),
    dict(
        key="wire_drawer",
        name="Wire Drawer",
        icon="🔌",
        output_key="copper_wire",
        output_amount=1,
        inputs=[("copper_ore", 1)],
    ),
    dict(
        key="glassworks",
        name="Glassworks",
        icon="🧊",
        output_key="glass",
        output_amount=1,
        inputs=[("silica", 1)],
    ),
    dict(
        key="motor_assembler",
        name="Motor Assembler",
        icon="🧲",
        output_key="electric_motor",
        output_amount=1,
        inputs=[("steel", 1), ("copper_wire", 1)],
    ),
    dict(
        key="drill_press",
        name="Drill Press",
        icon="⚒",
        output_key="mining_drill",
        output_amount=1,
        inputs=[("steel", 1), ("electric_motor", 1)],
    ),
    dict(
        key="control_fabricator",
        name="Control Fabricator",
        icon="💠",
        output_key="control_module",
        output_amount=1,
        inputs=[("copper_wire", 1), ("glass", 1), ("charged_crystal", 1)],
    ),
]


def seed_machine_definitions(db: Session) -> None:
    existing_keys = {row.key for row in db.query(MachineDefinition.key).all()}

    for entry in MACHINE_SEED:
        if entry["key"] in existing_keys:
            continue

        output_resource_id = db.scalar(select(ResourceDefinition.id).where(ResourceDefinition.key == entry["output_key"]))

        definition = MachineDefinition(
            key=entry["key"],
            name=entry["name"],
            icon=entry["icon"],
            output_resource_id=output_resource_id,
            output_amount=entry["output_amount"],
        )
        db.add(definition)
        db.flush()

        for resource_key, quantity in entry["inputs"]:
            resource_id = db.scalar(select(ResourceDefinition.id).where(ResourceDefinition.key == resource_key))
            db.add(
                MachineDefinitionInput(
                    machine_definition_id=definition.id,
                    resource_id=resource_id,
                    quantity=quantity,
                )
            )

    db.commit()
