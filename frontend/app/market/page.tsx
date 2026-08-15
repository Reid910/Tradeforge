"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Nav from "@/components/Nav";
import { api, ApiError, type MarketOrderOut } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { type MarketWsEvent, type MarketWsStatus, useMarketSocket } from "@/lib/useMarketSocket";

function money(value: string): string {
  return Number(value).toFixed(2);
}

export default function MarketPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading: authLoading, isError: authError } = useAuth();

  useEffect(() => {
    if (!authLoading && (authError || !user)) {
      router.replace("/login");
    }
  }, [authLoading, authError, user, router]);

  const [error, setError] = useState<string | null>(null);
  const [resourceKey, setResourceKey] = useState<string | null>(null);
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("");

  const { data: resources } = useQuery({
    queryKey: ["tradable-resources"],
    queryFn: api.getTradableResources,
    enabled: !!user,
  });

  useEffect(() => {
    if (!resourceKey && resources && resources.length > 0) {
      setResourceKey(resources[0].key);
    }
  }, [resourceKey, resources]);

  const { data: orderBook } = useQuery({
    queryKey: ["order-book", resourceKey],
    queryFn: () => api.getOrderBook(resourceKey!),
    enabled: !!user && !!resourceKey,
  });

  const { data: trades } = useQuery({
    queryKey: ["trades", resourceKey],
    queryFn: () => api.getTrades(resourceKey!),
    enabled: !!user && !!resourceKey,
  });

  const { data: myOrders } = useQuery({
    queryKey: ["my-orders"],
    queryFn: api.getMyOrders,
    enabled: !!user,
  });

  const { data: inventory } = useQuery({
    queryKey: ["inventory"],
    queryFn: api.getInventory,
    enabled: !!user,
  });

  const invalidateMarket = useCallback(
    (key: string) => {
      queryClient.invalidateQueries({ queryKey: ["order-book", key] });
      queryClient.invalidateQueries({ queryKey: ["trades", key] });
      queryClient.invalidateQueries({ queryKey: ["my-orders"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    [queryClient]
  );

  // The server never sends full state over the socket - every event just
  // means "something about this resource's market changed," so the
  // simplest correct response is the same invalidate-and-refetch pattern
  // already used everywhere else in this app (factory page's mutations),
  // not hand-rolled WS-delta cache patching.
  const handleWsEvent = useCallback(
    (event: MarketWsEvent) => invalidateMarket(event.resource_key),
    [invalidateMarket]
  );
  const wsStatus = useMarketSocket(resourceKey, handleWsEvent);

  const reportError = (err: unknown, fallback: string) => setError(err instanceof ApiError ? err.message : fallback);

  const createOrderMutation = useMutation({
    mutationFn: api.createOrder,
    onSuccess: (_order, variables) => {
      invalidateMarket(variables.resource_key);
      setPrice("");
      setQuantity("");
    },
    onError: (err) => reportError(err, "Couldn't place order"),
  });

  const cancelOrderMutation = useMutation({
    mutationFn: (orderId: number) => api.cancelOrder(orderId),
    onSuccess: (_void, orderId) => {
      const cancelled = myOrders?.find((o) => o.id === orderId);
      if (cancelled) invalidateMarket(cancelled.resource.key);
    },
    onError: (err) => reportError(err, "Couldn't cancel order"),
  });

  if (authLoading || !user) {
    return <div className="flex h-screen items-center justify-center text-sm text-slate-500">Loading…</div>;
  }

  const selectedResource = resources?.find((r) => r.key === resourceKey) ?? null;
  const inventoryItem = inventory?.items.find((i) => i.resource.key === resourceKey) ?? null;
  const availableQuantity = inventoryItem ? inventoryItem.quantity - inventoryItem.reserved_quantity : 0;
  const availableBalance = Number(user.balance) - Number(user.reserved_balance);
  const bestBid = orderBook?.buy_orders[0]?.price ?? null;
  const bestAsk = orderBook?.sell_orders[0]?.price ?? null;

  const openMyOrders = (myOrders ?? []).filter((o) => o.status === "open");

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-forge-border bg-forge-panel px-4 py-3">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide text-slate-100">
            TRADEFORGE <span className="text-slate-500">/ market</span>
          </h1>
          <Nav />
        </div>
        <WsStatusIndicator status={wsStatus} />
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
        <section className="flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Resource</label>
            <select
              value={resourceKey ?? ""}
              onChange={(e) => setResourceKey(e.target.value)}
              className="mt-1 block rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-sm text-slate-100 focus:border-forge-accent/60 focus:outline-none"
            >
              {(resources ?? []).map((r) => (
                <option key={r.key} value={r.key}>
                  {r.icon} {r.name}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-xs">
            <div className="text-slate-500">Balance</div>
            <div className="text-slate-100">
              ${money(user.balance)}{" "}
              {Number(user.reserved_balance) > 0 && (
                <span className="text-slate-500">(${money(user.reserved_balance)} reserved)</span>
              )}
            </div>
          </div>

          {selectedResource && (
            <div className="rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-xs">
              <div className="text-slate-500">
                {selectedResource.icon} {selectedResource.name} held
              </div>
              <div className="text-slate-100">
                {inventoryItem?.quantity ?? 0}{" "}
                {inventoryItem && inventoryItem.reserved_quantity > 0 && (
                  <span className="text-slate-500">({inventoryItem.reserved_quantity} reserved)</span>
                )}
              </div>
            </div>
          )}

          <div className="rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-xs">
            <div className="text-slate-500">Best bid / ask</div>
            <div className="text-slate-100">
              <span className="text-emerald-400">{bestBid ? `$${money(bestBid)}` : "—"}</span>
              {" / "}
              <span className="text-red-400">{bestAsk ? `$${money(bestAsk)}` : "—"}</span>
            </div>
          </div>
        </section>

        {resourceKey && (
          <section className="mt-6">
            <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Place order</h2>
            <form
              className="mt-2 flex flex-wrap items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createOrderMutation.mutate({ resource_key: resourceKey, side, price, quantity: Number(quantity) });
              }}
            >
              <div className="flex overflow-hidden rounded-md border border-forge-border">
                <button
                  type="button"
                  onClick={() => setSide("buy")}
                  className={`px-3 py-2 text-xs font-medium ${
                    side === "buy" ? "bg-emerald-500/20 text-emerald-400" : "text-slate-400 hover:text-slate-100"
                  }`}
                >
                  Buy
                </button>
                <button
                  type="button"
                  onClick={() => setSide("sell")}
                  className={`px-3 py-2 text-xs font-medium ${
                    side === "sell" ? "bg-red-500/20 text-red-400" : "text-slate-400 hover:text-slate-100"
                  }`}
                >
                  Sell
                </button>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-wide text-slate-500">Price</label>
                <input
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="0.00"
                  inputMode="decimal"
                  className="mt-1 block w-28 rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-forge-accent/60 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-wide text-slate-500">Quantity</label>
                <input
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="0"
                  inputMode="numeric"
                  className="mt-1 block w-24 rounded-md border border-forge-border bg-forge-panel px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-forge-accent/60 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={createOrderMutation.isPending || !price || !quantity}
                className="rounded-md border border-forge-border px-3 py-2 text-sm text-slate-300 hover:border-forge-accent/60 hover:text-slate-100 disabled:opacity-50"
              >
                {side === "buy" ? "Place buy order" : "Place sell order"}
              </button>

              <span className="text-xs text-slate-500">
                {side === "sell" ? `${availableQuantity} available to sell` : `$${availableBalance.toFixed(2)} available`}
              </span>
            </form>
          </section>
        )}

        {openMyOrders.length > 0 && (
          <section className="mt-6">
            <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Your open orders</h2>
            <div className="mt-2 max-w-2xl overflow-hidden rounded-lg border border-forge-border">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-forge-border bg-forge-panel text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-2 font-medium">Resource</th>
                    <th className="px-4 py-2 font-medium">Side</th>
                    <th className="px-4 py-2 font-medium text-right">Price</th>
                    <th className="px-4 py-2 font-medium text-right">Remaining</th>
                    <th className="px-4 py-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {openMyOrders.map((order) => (
                    <tr key={order.id} className="border-b border-forge-border/50 last:border-0">
                      <td className="px-4 py-2 text-slate-100">
                        {order.resource.icon} {order.resource.name}
                      </td>
                      <td className={`px-4 py-2 ${order.side === "buy" ? "text-emerald-400" : "text-red-400"}`}>
                        {order.side}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-100">${money(order.price)}</td>
                      <td className="px-4 py-2 text-right text-slate-100">
                        {order.remaining_quantity} / {order.original_quantity}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => cancelOrderMutation.mutate(order.id)}
                          disabled={cancelOrderMutation.isPending && cancelOrderMutation.variables === order.id}
                          className="text-xs text-slate-500 hover:text-red-400 disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {resourceKey && (
          <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Order book</h2>
              <div className="mt-2 grid grid-cols-2 gap-3">
                <OrderSideTable title="Bids" orders={orderBook?.buy_orders ?? []} tone="text-emerald-400" />
                <OrderSideTable title="Asks" orders={orderBook?.sell_orders ?? []} tone="text-red-400" />
              </div>
            </div>

            <div>
              <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Recent trades</h2>
              <div className="mt-2 overflow-hidden rounded-lg border border-forge-border">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-forge-border bg-forge-panel text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-3 py-2 font-medium text-right">Price</th>
                      <th className="px-3 py-2 font-medium text-right">Qty</th>
                      <th className="px-3 py-2 font-medium text-right">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(trades ?? []).length === 0 && (
                      <tr>
                        <td colSpan={3} className="px-3 py-2 text-xs text-slate-500">
                          No trades yet.
                        </td>
                      </tr>
                    )}
                    {(trades ?? []).map((trade) => (
                      <tr key={trade.id} className="border-b border-forge-border/50 last:border-0">
                        <td className="px-3 py-2 text-right text-slate-100">${money(trade.price)}</td>
                        <td className="px-3 py-2 text-right text-slate-400">{trade.quantity}</td>
                        <td className="px-3 py-2 text-right text-slate-500">
                          {new Date(trade.created_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function OrderSideTable({ title, orders, tone }: { title: string; orders: MarketOrderOut[]; tone: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-forge-border">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-forge-border bg-forge-panel text-xs uppercase tracking-wide text-slate-500">
            <th className="px-3 py-2 font-medium">{title}</th>
            <th className="px-3 py-2 font-medium text-right">Qty</th>
          </tr>
        </thead>
        <tbody>
          {orders.length === 0 && (
            <tr>
              <td colSpan={2} className="px-3 py-2 text-xs text-slate-500">
                None
              </td>
            </tr>
          )}
          {orders.map((order) => (
            <tr key={order.id} className="border-b border-forge-border/50 last:border-0">
              <td className={`px-3 py-2 ${tone}`}>${money(order.price)}</td>
              <td className="px-3 py-2 text-right text-slate-100">{order.remaining_quantity}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WsStatusIndicator({ status }: { status: MarketWsStatus }) {
  const dotClass =
    status === "open"
      ? "bg-emerald-400"
      : status === "connecting" || status === "reconnecting"
        ? "bg-amber-400"
        : "bg-red-500";
  const label = status === "open" ? "live" : status === "connecting" ? "connecting" : status === "reconnecting" ? "reconnecting" : "offline";

  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-400">
      <span className={`h-2 w-2 rounded-full ${dotClass} ${status !== "open" ? "animate-pulse" : ""}`} />
      Market {label}
    </span>
  );
}
