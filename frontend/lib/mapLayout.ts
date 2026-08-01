export interface Point {
  x: number;
  y: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
}

const RADIUS_STEP = 170;

/**
 * Radial tree layout: root at center, each depth ring further out, each
 * subtree given an angular slice proportional to its leaf count. Since the
 * map is a tree (one path between any two nodes), this guarantees edges
 * never cross.
 */
export function computeRadialLayout(edges: LayoutEdge[], rootId: string): Record<string, Point> {
  const children: Record<string, string[]> = {};
  for (const edge of edges) {
    (children[edge.source] ??= []).push(edge.target);
  }

  const leafCountCache = new Map<string, number>();
  const leafCount = (id: string): number => {
    const cached = leafCountCache.get(id);
    if (cached !== undefined) return cached;
    const kids = children[id];
    const count = !kids || kids.length === 0 ? 1 : kids.reduce((sum, c) => sum + leafCount(c), 0);
    leafCountCache.set(id, count);
    return count;
  };

  const positions: Record<string, Point> = { [rootId]: { x: 0, y: 0 } };

  const place = (id: string, angleStart: number, angleEnd: number, depth: number) => {
    const kids = children[id] ?? [];
    if (kids.length === 0) return;

    const total = kids.reduce((sum, c) => sum + leafCount(c), 0);
    const radius = depth * RADIUS_STEP;
    let cursor = angleStart;

    for (const child of kids) {
      const share = (angleEnd - angleStart) * (leafCount(child) / total);
      const angle = cursor + share / 2;
      positions[child] = { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
      place(child, cursor, cursor + share, depth + 1);
      cursor += share;
    }
  };

  place(rootId, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2, 1);

  return positions;
}
