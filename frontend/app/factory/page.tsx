"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import FactoryCanvas from "@/components/factory/FactoryCanvas";
import MachinePalette from "@/components/factory/MachinePalette";
import Nav from "@/components/Nav";
import { api, ApiError } from "@/lib/api";
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

  const [armedKey, setArmedKey] = useState<string | null>(null);
  const [selectedGridId, setSelectedGridId] = useState<number | null>(null);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const { data: definitions } = useQuery({
    queryKey: ["machine-definitions"],
    queryFn: api.getMachineDefinitions,
    enabled: !!user,
  });

  const { data: grids, isLoading: gridsLoading, isError: gridsError } = useQuery({
    queryKey: ["factory-grids"],
    queryFn: api.getFactoryGrids,
    enabled: !!user,
  });

  const unlockMutation = useMutation({
    mutationFn: api.unlockFactoryGrid,
    onSuccess: (grid) => {
      queryClient.invalidateQueries({ queryKey: ["factory-grids"] });
      setSelectedGridId(grid.id);
    },
    onError: (err) => setUnlockError(err instanceof ApiError ? err.message : "Couldn't unlock a new grid"),
  });

  const selectedGrid = grids?.find((g) => g.id === selectedGridId) ?? grids?.[0] ?? null;

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

        {grids && grids.length > 0 && (
          <div className="flex items-center gap-2">
            {grids.map((g) => (
              <button
                key={g.id}
                onClick={() => setSelectedGridId(g.id)}
                className={`rounded-md px-2 py-1 text-xs font-medium ${
                  (selectedGrid?.id ?? grids[0].id) === g.id
                    ? "bg-forge-border/60 text-slate-100"
                    : "text-slate-400 hover:bg-forge-border/40 hover:text-slate-100"
                }`}
              >
                Grid {g.slot_index}
              </button>
            ))}
            <button
              onClick={() => unlockMutation.mutate()}
              disabled={unlockMutation.isPending}
              className="rounded-md border border-forge-border px-2 py-1 text-xs text-slate-400 hover:border-forge-accent/60 hover:text-slate-100 disabled:opacity-50"
            >
              + Unlock grid
            </button>
          </div>
        )}
      </header>

      {unlockError && (
        <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-1.5 text-xs text-red-400">
          {unlockError}
          <button onClick={() => setUnlockError(null)} className="ml-2 text-red-300 hover:text-red-100">
            ✕
          </button>
        </div>
      )}

      <main className="flex flex-1 overflow-hidden">
        {definitions && (
          <MachinePalette definitions={definitions} armedKey={armedKey} onArm={setArmedKey} />
        )}

        <div className="flex-1">
          {gridsLoading && (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading factory…</div>
          )}
          {gridsError && (
            <div className="flex h-full items-center justify-center text-sm text-red-400">
              Failed to load the factory. Try refreshing.
            </div>
          )}
          {selectedGrid && (
            <FactoryCanvas grid={selectedGrid} armedKey={armedKey} onArmedConsumed={() => setArmedKey(null)} />
          )}
        </div>
      </main>
    </div>
  );
}
