"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Nav from "@/components/Nav";
import { api, ApiError, type MachineOut } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

export default function FactoryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading: authLoading, isError: authError } = useAuth();

  useEffect(() => {
    if (!authLoading && (authError || !user)) {
      router.replace("/login");
    }
  }, [authLoading, authError, user, router]);

  const [error, setError] = useState<string | null>(null);

  const { data: definitions } = useQuery({
    queryKey: ["machine-definitions"],
    queryFn: api.getMachineDefinitions,
    enabled: !!user,
  });

  const { data: machines, isLoading: machinesLoading, isError: machinesError } = useQuery({
    queryKey: ["machines"],
    queryFn: api.getMachines,
    enabled: !!user,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["machines"] });
  const reportError = (err: unknown, fallback: string) => setError(err instanceof ApiError ? err.message : fallback);

  const createMutation = useMutation({
    mutationFn: (key: string) => api.createMachine(key),
    onSuccess: invalidate,
    onError: (err) => reportError(err, "Couldn't add machine"),
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => api.removeMachine(id),
    onSuccess: invalidate,
  });

  const toggleMutation = useMutation({
    mutationFn: (id: number) => api.toggleMachine(id),
    onSuccess: invalidate,
  });

  const craftMutation = useMutation({
    mutationFn: (id: number) => api.craftMachine(id),
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
    onError: (err) => reportError(err, "Couldn't craft"),
  });

  if (authLoading || !user) {
    return <div className="flex h-screen items-center justify-center text-sm text-slate-500">Loading…</div>;
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-forge-border bg-forge-panel px-4 py-3">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide text-slate-100">
            TRADEFORGE <span className="text-slate-500">/ factory</span>
          </h1>
          <Nav />
        </div>
      </header>

      {error && (
        <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-1.5 text-xs text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-100">
            ✕
          </button>
        </div>
      )}

      <main className="flex-1 overflow-auto p-4 sm:p-6">
        <section>
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Add a machine</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {definitions?.map((def) => (
              <button
                key={def.key}
                onClick={() => createMutation.mutate(def.key)}
                disabled={createMutation.isPending}
                className="flex items-center gap-2 rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-sm hover:border-forge-accent/60 disabled:opacity-50"
              >
                <span className="text-lg leading-none">{def.icon}</span>
                <span className="text-slate-100">{def.name}</span>
                <span className="text-xs text-slate-500">
                  {def.inputs.map((i) => `${i.quantity}${i.resource.icon}`).join("+")} → {def.output_amount}
                  {def.output_resource.icon}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6">
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Your machines</h2>

          {machinesLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
          {machinesError && <p className="mt-2 text-sm text-red-400">Failed to load machines.</p>}
          {machines && machines.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No machines yet — add one above.</p>
          )}

          <div className="mt-2 space-y-2">
            {machines?.map((machine) => (
              <MachineRow
                key={machine.id}
                machine={machine}
                onToggle={() => toggleMutation.mutate(machine.id)}
                onCraft={() => craftMutation.mutate(machine.id)}
                onRemove={() => removeMutation.mutate(machine.id)}
                crafting={craftMutation.isPending && craftMutation.variables === machine.id}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function MachineRow({
  machine,
  onToggle,
  onCraft,
  onRemove,
  crafting,
}: {
  machine: MachineOut;
  onToggle: () => void;
  onCraft: () => void;
  onRemove: () => void;
  crafting: boolean;
}) {
  const { definition } = machine;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-forge-border bg-forge-panel p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <span className="text-2xl leading-none">{definition.icon}</span>
        <div>
          <div className="text-sm font-medium text-slate-100">{definition.name}</div>
          <div className="text-xs text-slate-500">
            {definition.inputs.map((i) => `${i.quantity} ${i.resource.icon}`).join(" + ")} → {definition.output_amount}{" "}
            {definition.output_resource.icon}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onToggle}
          className={`rounded-md border px-2 py-1 text-xs font-medium ${
            machine.active
              ? "border-forge-accent/60 bg-forge-accent/10 text-forge-accent"
              : "border-forge-border text-slate-400"
          }`}
        >
          {machine.active ? "Active" : "Paused"}
        </button>
        <button
          onClick={onCraft}
          disabled={crafting}
          className="rounded-md border border-forge-border px-2 py-1 text-xs text-slate-300 hover:border-forge-accent/60 hover:text-slate-100 disabled:opacity-50"
        >
          Craft now
        </button>
        <button
          onClick={onRemove}
          className="rounded-md border border-forge-border px-2 py-1 text-xs text-slate-500 hover:border-red-500/50 hover:text-red-400"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
