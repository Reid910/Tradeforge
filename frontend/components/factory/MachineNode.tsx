"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { MachineOut } from "@/lib/api";

export interface MachineNodeData extends MachineOut {
  onDelete: (machineId: number) => void;
}

export default function MachineNode({ data }: NodeProps & { data: MachineNodeData }) {
  const { definition } = data;

  return (
    <div className="group relative flex h-28 w-28 flex-col items-center justify-center gap-0.5 rounded-lg border-2 border-forge-accent bg-forge-panel p-2 text-center shadow-[0_0_12px_-2px_rgba(224,163,57,0.4)]">
      <Handle type="target" position={Position.Left} className="!bg-forge-border" />
      <Handle type="source" position={Position.Right} className="!bg-forge-border" />

      <span className="text-2xl leading-none">{definition.icon}</span>
      <span className="truncate text-[10px] font-medium text-slate-200">{definition.name}</span>
      <span className="text-[10px] text-slate-500">
        {definition.inputs.map((i) => i.resource.icon).join("")} → {definition.output_resource.icon}
      </span>

      <button
        onClick={(event) => {
          event.stopPropagation();
          data.onDelete(data.id);
        }}
        className="absolute -right-2 -top-2 hidden h-5 w-5 items-center justify-center rounded-full border border-forge-border bg-forge-bg text-[10px] text-slate-400 hover:text-red-400 group-hover:flex"
        aria-label={`Remove ${definition.name}`}
      >
        ✕
      </button>
    </div>
  );
}
