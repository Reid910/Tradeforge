from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.map_node import MapNode
from app.models.resource import ResourceDefinition
from app.schemas.map import MapEdgeOut, MapNodeOut, MapResponse, ResourceOut
from app.services import map_template


def seed_user_map(db: Session, user_id: int) -> None:
    """Create this user's copy of the shared map template, root unlocked."""
    direct_children = set(map_template.children_of(map_template.ROOT_KEY))

    for template in map_template.NODE_TEMPLATES:
        resource_id = None
        if template.resource_key is not None:
            resource_id = db.scalar(
                select(ResourceDefinition.id).where(ResourceDefinition.key == template.resource_key)
            )

        if template.key == map_template.ROOT_KEY:
            initial_status = "unlocked"
        elif template.key in direct_children:
            initial_status = "discovered"
        else:
            initial_status = "locked"

        db.add(
            MapNode(
                user_id=user_id,
                node_key=template.key,
                resource_id=resource_id,
                status=initial_status,
            )
        )

    db.commit()


def get_user_map(db: Session, user_id: int) -> MapResponse:
    rows = db.query(MapNode).filter(MapNode.user_id == user_id).all()

    nodes = [
        MapNodeOut(
            node_key=row.node_key,
            status=row.status,
            resource=ResourceOut.model_validate(row.resource) if row.resource_id else None,
        )
        for row in rows
    ]
    edges = [MapEdgeOut(source=s, target=t) for s, t in map_template.edges()]
    return MapResponse(nodes=nodes, edges=edges)


def unlock_node(db: Session, user_id: int, node_key: str) -> tuple[str, list[str]]:
    target = db.execute(
        select(MapNode)
        .where(MapNode.user_id == user_id, MapNode.node_key == node_key)
        .with_for_update(of=MapNode)
    ).scalar_one_or_none()

    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    if target.status == "unlocked":
        return target.node_key, []

    if target.status != "discovered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Node must be discovered before it can be unlocked",
        )

    target.status = "unlocked"

    child_keys = map_template.children_of(node_key)
    newly_discovered: list[str] = []
    if child_keys:
        children = db.execute(
            select(MapNode)
            .where(MapNode.user_id == user_id, MapNode.node_key.in_(child_keys))
            .with_for_update(of=MapNode)
        ).scalars().all()
        for child in children:
            if child.status == "locked":
                child.status = "discovered"
                newly_discovered.append(child.node_key)

    db.commit()
    return target.node_key, newly_discovered
