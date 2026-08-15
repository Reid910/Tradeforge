from sqlalchemy.orm import Session

from app.models.resource import ResourceDefinition

RESOURCE_SEED = [
    dict(key="iron_ore", name="Iron Ore", category="raw", icon="⛏", base_value="5", yield_amount=2, rarity="common"),
    dict(key="coal", name="Coal", category="raw", icon="🪨", base_value="3", yield_amount=3, rarity="common"),
    dict(key="copper_ore", name="Copper Ore", category="raw", icon="🔶", base_value="6", yield_amount=2, rarity="common"),
    dict(key="silica", name="Silica", category="raw", icon="🏜", base_value="4", yield_amount=2, rarity="common"),
    dict(key="charged_crystal", name="Charged Crystal", category="rare", icon="💎", base_value="50", yield_amount=1, rarity="rare"),
    dict(key="prismatic_core", name="Prismatic Core", category="rare", icon="🔮", base_value="120", yield_amount=1, rarity="rare"),
    # Intermediate/factory-produced resources. yield_amount is unused here -
    # it only means something for resources tied to a mine node.
    dict(key="copper_ingot", name="Copper Ingot", category="intermediate", icon="🧱", base_value="18", yield_amount=1, rarity="common"),
    dict(key="copper_plate", name="Copper Plate", category="finished", icon="🟫", base_value="45", yield_amount=1, rarity="common"),
    dict(key="steel", name="Steel", category="intermediate", icon="⚙", base_value="25", yield_amount=1, rarity="common"),
    dict(key="copper_wire", name="Copper Wire", category="intermediate", icon="🔌", base_value="15", yield_amount=1, rarity="common"),
    dict(key="glass", name="Glass", category="intermediate", icon="🧊", base_value="10", yield_amount=1, rarity="common"),
    dict(key="electric_motor", name="Electric Motor", category="finished", icon="🧲", base_value="80", yield_amount=1, rarity="common"),
    dict(key="mining_drill", name="Mining Drill", category="finished", icon="🛠", base_value="150", yield_amount=1, rarity="common"),
    dict(key="control_module", name="Control Module", category="finished", icon="💠", base_value="200", yield_amount=1, rarity="rare"),
]


def seed_resources(db: Session) -> None:
    existing_keys = {row.key for row in db.query(ResourceDefinition.key).all()}
    for entry in RESOURCE_SEED:
        if entry["key"] not in existing_keys:
            db.add(ResourceDefinition(**entry, tradable=True))
    db.commit()
