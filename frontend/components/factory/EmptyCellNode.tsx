"use client";

import type { NodeProps } from "@xyflow/react";

export interface EmptyCellNodeData {
  [key: string]: unknown;
  x: number;
  y: number;
  armed: boolean;
  onPlace: (x: number, y: number) => void;
}

export default function EmptyCellNode({ data }: NodeProps & { data: EmptyCellNodeData }) {
  return (
    <button
      onClick={() => data.armed && data.onPlace(data.x, data.y)}
      disabled={!data.armed}
      className={`h-28 w-28 rounded-lg border-2 border-dashed transition-colors ${
        data.armed
          ? "cursor-pointer border-forge-accent/50 hover:border-forge-accent hover:bg-forge-accent/10"
          : "cursor-default border-forge-border/40"
      }`}
      aria-label={`Empty cell ${data.x},${data.y}`}
    />
  );
}
