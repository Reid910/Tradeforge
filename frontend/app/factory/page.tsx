"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Nav from "@/components/Nav";
import { api, ApiError, type MachineChainOut, type MachineDefinitionOut } from "@/lib/api";
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
  const [newChainName, setNewChainName] = useState("");

  const { data: definitions } = useQuery({
    queryKey: ["machine-definitions"],
    queryFn: api.getMachineDefinitions,
    enabled: !!user,
  });

  const { data: chains, isLoading: chainsLoading, isError: chainsError } = useQuery({
    queryKey: ["chains"],
    queryFn: api.getChains,
    enabled: !!user,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["chains"] });
  const reportError = (err: unknown, fallback: string) => setError(err instanceof ApiError ? err.message : fallback);

  const createChainMutation = useMutation({
    mutationFn: (name: string) => api.createChain(name),
    onSuccess: () => {
      invalidate();
      setNewChainName("");
    },
    onError: (err) => reportError(err, "Couldn't create chain"),
  });

  const removeChainMutation = useMutation({
    mutationFn: (chainId: number) => api.removeChain(chainId),
    onSuccess: invalidate,
  });

  const toggleChainMutation = useMutation({
    mutationFn: (chainId: number) => api.toggleChain(chainId),
    onSuccess: invalidate,
  });

  const runChainMutation = useMutation({
    mutationFn: (chainId: number) => api.runChain(chainId),
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
    onError: (err) => reportError(err, "Couldn't run chain"),
  });

  const addMachineMutation = useMutation({
    mutationFn: ({ chainId, key }: { chainId: number; key: string }) => api.addMachine(chainId, key),
    onSuccess: invalidate,
    onError: (err) => reportError(err, "Couldn't add machine"),
  });

  const removeMachineMutation = useMutation({
    mutationFn: ({ chainId, machineId }: { chainId: number; machineId: number }) =>
      api.removeMachine(chainId, machineId),
    onSuccess: invalidate,
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
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">New chain</h2>
          <form
            className="mt-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (newChainName.trim()) createChainMutation.mutate(newChainName.trim());
            }}
          >
            <input
              value={newChainName}
              onChange={(e) => setNewChainName(e.target.value)}
              placeholder="e.g. Copper Line"
              className="rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-forge-accent/60 focus:outline-none"
            />
            <button
              type="submit"
              disabled={createChainMutation.isPending || !newChainName.trim()}
              className="rounded-md border border-forge-border px-3 py-2 text-sm text-slate-300 hover:border-forge-accent/60 hover:text-slate-100 disabled:opacity-50"
            >
              Create chain
            </button>
          </form>
        </section>

        <section className="mt-6">
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Your chains</h2>

          {chainsLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
          {chainsError && <p className="mt-2 text-sm text-red-400">Failed to load chains.</p>}
          {chains && chains.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No chains yet — create one above.</p>
          )}

          <div className="mt-2 space-y-4">
            {chains?.map((chain) => (
              <ChainCard
                key={chain.id}
                chain={chain}
                definitions={definitions ?? []}
                onToggle={() => toggleChainMutation.mutate(chain.id)}
                onRun={() => runChainMutation.mutate(chain.id)}
                onRemoveChain={() => removeChainMutation.mutate(chain.id)}
                onAddMachine={(key) => addMachineMutation.mutate({ chainId: chain.id, key })}
                onRemoveMachine={(machineId) => removeMachineMutation.mutate({ chainId: chain.id, machineId })}
                running={runChainMutation.isPending && runChainMutation.variables === chain.id}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function ChainCard({
  chain,
  definitions,
  onToggle,
  onRun,
  onRemoveChain,
  onAddMachine,
  onRemoveMachine,
  running,
}: {
  chain: MachineChainOut;
  definitions: MachineDefinitionOut[];
  onToggle: () => void;
  onRun: () => void;
  onRemoveChain: () => void;
  onAddMachine: (key: string) => void;
  onRemoveMachine: (machineId: number) => void;
  running: boolean;
}) {
  return (
    <div className="rounded-lg border border-forge-border bg-forge-panel p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-slate-100">{chain.name}</span>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={onToggle}
            className={`rounded-md border px-2 py-1 text-xs font-medium ${
              chain.active
                ? "border-forge-accent/60 bg-forge-accent/10 text-forge-accent"
                : "border-forge-border text-slate-400"
            }`}
          >
            {chain.active ? "Active" : "Paused"}
          </button>
          <button
            onClick={onRun}
            disabled={chain.active || running}
            title={chain.active ? "Pause the chain to run it manually" : undefined}
            className="rounded-md border border-forge-border px-2 py-1 text-xs text-slate-300 hover:border-forge-accent/60 hover:text-slate-100 disabled:opacity-50"
          >
            Run now
          </button>
          <button
            onClick={onRemoveChain}
            className="rounded-md border border-forge-border px-2 py-1 text-xs text-slate-500 hover:border-red-500/50 hover:text-red-400"
          >
            Delete chain
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {chain.machines.length === 0 && <span className="text-xs text-slate-500">No machines yet.</span>}

        {chain.machines.map((machine, index) => (
          <div key={machine.id} className="flex items-center gap-2">
            {index > 0 && <span className="text-slate-600">→</span>}
            <div className="group relative flex items-center gap-2 rounded-md border border-forge-border bg-forge-bg px-2 py-1.5">
              <span className="text-lg leading-none">{machine.definition.icon}</span>
              <div className="text-xs">
                <div className="text-slate-100">{machine.definition.name}</div>
                <div className="text-slate-500">
                  {machine.definition.inputs.map((i) => `${i.quantity}${i.resource.icon}`).join("+")} →{" "}
                  {machine.definition.output_amount}
                  {machine.definition.output_resource.icon}
                </div>
              </div>
              <button
                onClick={() => onRemoveMachine(machine.id)}
                className="ml-1 text-slate-600 hover:text-red-400"
                title="Remove machine"
              >
                ✕
              </button>
            </div>
          </div>
        ))}

        {chain.machines.length > 0 && <span className="text-slate-600">→</span>}
        <AddMachineMenu definitions={definitions} onAdd={onAddMachine} />
      </div>
    </div>
  );
}

function AddMachineMenu({
  definitions,
  onAdd,
}: {
  definitions: MachineDefinitionOut[];
  onAdd: (key: string) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded-md border border-dashed border-forge-border px-2 py-1.5 text-xs text-slate-400 hover:border-forge-accent/60 hover:text-slate-100"
      >
        + Add machine
      </button>

      {open && (
        <div className="absolute left-0 top-full z-10 mt-1 flex min-w-[220px] flex-col gap-1 rounded-md border border-forge-border bg-forge-panel p-2 shadow-lg">
          {definitions.length === 0 && <span className="px-2 py-1 text-xs text-slate-500">No machine types yet.</span>}
          {definitions.map((def) => (
            <button
              key={def.key}
              onClick={() => {
                onAdd(def.key);
                setOpen(false);
              }}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-forge-bg"
            >
              <span className="text-base leading-none">{def.icon}</span>
              <span className="text-slate-100">{def.name}</span>
              <span className="text-slate-500">
                {def.inputs.map((i) => `${i.quantity}${i.resource.icon}`).join("+")} → {def.output_amount}
                {def.output_resource.icon}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
