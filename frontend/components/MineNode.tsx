"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { MapNodeOut } from "@/lib/api";

// Handles are pinned to the node's center (overriding React Flow's default
// edge placement) so radial edges connect center-to-center and disappear
// behind the circle, instead of visibly kinking at a fixed top/bottom point.
const centeredHandleStyle: React.CSSProperties = {
  top: "50%",
  left: "50%",
  transform: "translate(-50%, -50%)",
  width: 1,
  height: 1,
  minWidth: 0,
  minHeight: 0,
  border: "none",
  background: "transparent",
  opacity: 0,
};

const CIRCLE_STYLES: Record<MapNodeOut["status"], string> = {
  unlocked: "border-forge-accent bg-forge-panel shadow-[0_0_16px_-2px_rgba(224,163,57,0.55)]",
  discovered: "border-dashed border-slate-500 bg-forge-panel hover:border-forge-accent/70",
  locked: "border-forge-border bg-[#0f1114] grayscale opacity-50",
};

export default function MineNode({ data }: NodeProps & { data: MapNodeOut }) {
  const resource = data.resource;
  const isHub = !resource;
  const isRare = resource?.rarity === "rare";
  const size = isHub ? "h-20 w-20" : "h-16 w-16";

  return (
    <div className={`relative flex items-center justify-center ${size}`}>
      <Handle type="target" position={Position.Top} style={centeredHandleStyle} />
      <Handle type="source" position={Position.Bottom} style={centeredHandleStyle} />

      {isRare && data.status !== "locked" && (
        <span className="absolute -inset-1 rounded-full ring-2 ring-forge-rare/70" />
      )}
      {data.status === "discovered" && (
        <span className="absolute -inset-1 animate-pulse rounded-full border border-slate-500/50" />
      )}

      <div
        className={`relative flex h-full w-full cursor-pointer items-center justify-center rounded-full border-2 text-2xl transition-colors ${CIRCLE_STYLES[data.status]}`}
      >
        {resource ? resource.icon : "🏠"}
      </div>

      {data.status === "locked" && (
        <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full border border-forge-border bg-forge-bg text-[9px]">
          🔒
        </span>
      )}

      {!isHub && (
        <span
          className={`absolute -bottom-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full border-2 border-forge-bg text-xl font-bold ${
            data.status === "unlocked" ? "bg-forge-accent text-forge-bg" : "bg-forge-border/70 text-slate-500"
          }`}
        >
          {resource?.yield_amount}
        </span>
      )}
    </div>
  );
}
