"use client";

import type { MachineDefinitionOut } from "@/lib/api";

export default function MachinePalette({
  definitions,
  armedKey,
  onArm,
}: {
  definitions: MachineDefinitionOut[];
  armedKey: string | null;
  onArm: (key: string | null) => void;
}) {
  return (
    <aside className="w-56 shrink-0 border-r border-forge-border bg-forge-panel p-3">
      <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Machines</h2>
      <div className="mt-2 space-y-2">
        {definitions.map((def) => {
          const armed = armedKey === def.key;
          return (
            <button
              key={def.key}
              onClick={() => onArm(armed ? null : def.key)}
              className={`w-full rounded-md border p-2 text-left text-xs transition-colors ${
                armed
                  ? "border-forge-accent bg-forge-accent/10"
                  : "border-forge-border hover:border-forge-accent/50"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg leading-none">{def.icon}</span>
                <span className="font-medium text-slate-100">{def.name}</span>
              </div>
              <div className="mt-1 text-slate-500">
                {def.inputs.map((i) => `${i.quantity} ${i.resource.icon}`).join(" + ")} → {def.output_amount}{" "}
                {def.output_resource.icon}
              </div>
            </button>
          );
        })}
      </div>

      {armedKey && (
        <p className="mt-3 text-[11px] text-slate-500">Click an empty cell to place it. Click the machine again to cancel.</p>
      )}
    </aside>
  );
}
