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
