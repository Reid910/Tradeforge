"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

export default function InventoryPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, isError: authError } = useAuth();

  useEffect(() => {
    if (!authLoading && (authError || !user)) {
      router.replace("/login");
    }
  }, [authLoading, authError, user, router]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["inventory"],
    queryFn: api.getInventory,
    enabled: !!user,
    // Matches the backend's mine tick length (settings.mine_tick_seconds) so
    // totals visibly climb while sitting on this page - production is fully
    // automatic, this is just how the UI notices it happened.
    refetchInterval: 6000,
  });

  if (authLoading || !user) {
    return <div className="flex h-screen items-center justify-center text-sm text-slate-500">Loading…</div>;
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-forge-border bg-forge-panel px-4 py-3">
        <h1 className="text-sm font-semibold tracking-wide text-slate-100">
          TRADEFORGE <span className="text-slate-500">/ inventory</span>
        </h1>
        <Link href="/" className="text-xs text-slate-400 hover:text-slate-200">
          Back to map
        </Link>
      </header>

      <main className="flex-1 overflow-auto p-6">
        {isLoading && <p className="text-sm text-slate-500">Loading inventory…</p>}
        {isError && <p className="text-sm text-red-400">Failed to load inventory.</p>}

        {data && data.items.length === 0 && (
          <p className="text-sm text-slate-500">Nothing collected yet — unlock a mine and collect from it.</p>
        )}

        {data && data.items.length > 0 && (
          <div className="max-w-2xl overflow-hidden rounded-lg border border-forge-border">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-forge-border bg-forge-panel text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2 font-medium">Resource</th>
                  <th className="px-4 py-2 font-medium">Category</th>
                  <th className="px-4 py-2 font-medium text-right">Quantity</th>
                  <th className="px-4 py-2 font-medium text-right">Reserved</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.resource.key} className="border-b border-forge-border/50 last:border-0">
                    <td className="flex items-center gap-2 px-4 py-2 text-slate-100">
                      <span className="text-lg leading-none">{item.resource.icon}</span>
                      {item.resource.name}
                      {item.resource.rarity === "rare" && (
                        <span className="rounded bg-forge-rare/20 px-1 text-[10px] font-medium text-forge-rare">
                          RARE
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 capitalize text-slate-400">{item.resource.category}</td>
                    <td className="px-4 py-2 text-right text-slate-100">{item.quantity}</td>
                    <td className="px-4 py-2 text-right text-slate-500">{item.reserved_quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
