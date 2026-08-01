"""Static map definition: the same mining tree for every player.

Deterministic and shared across users - only each user's per-node status
(locked/discovered/unlocked) lives in the database. Mirrors the shape that
used to be hardcoded in the frontend's lib/mapData.ts.
"""

from dataclasses import dataclass

ROOT_KEY = "start"


@dataclass(frozen=True)
class NodeTemplate:
    key: str
    resource_key: str | None
    parent_key: str | None


NODE_TEMPLATES: list[NodeTemplate] = [
    NodeTemplate("start", None, None),
    NodeTemplate("iron-1", "iron_ore", "start"),
    NodeTemplate("coal-1", "coal", "start"),
    NodeTemplate("copper-1", "copper_ore", "start"),
    NodeTemplate("iron-3", "iron_ore", "start"),
    NodeTemplate("iron-2", "iron_ore", "iron-1"),
    NodeTemplate("crystal-1", "charged_crystal", "iron-1"),
    NodeTemplate("coal-2", "coal", "coal-1"),
    NodeTemplate("silica-1", "silica", "coal-1"),
    NodeTemplate("copper-2", "copper_ore", "copper-1"),
    NodeTemplate("crystal-2", "prismatic_core", "copper-2"),
    NodeTemplate("silica-2", "silica", "silica-1"),
]

_BY_KEY = {t.key: t for t in NODE_TEMPLATES}


def edges() -> list[tuple[str, str]]:
    return [(t.parent_key, t.key) for t in NODE_TEMPLATES if t.parent_key is not None]


def children_of(node_key: str) -> list[str]:
    return [t.key for t in NODE_TEMPLATES if t.parent_key == node_key]


def resource_key_of(node_key: str) -> str | None:
    return _BY_KEY[node_key].resource_key
