"use client";

import { useEffect, useRef, useState } from "react";

import type { MarketOrderOut, TradeOut } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws") + "/ws/market";

const MAX_BACKOFF_MS = 15000;

export type MarketWsEvent =
  | { type: "market_snapshot_required"; resource_key: string; seq: number; data: Record<string, never> }
  | {
      type: "order_created" | "order_updated" | "order_cancelled";
      resource_key: string;
      seq: number;
      data: MarketOrderOut;
    }
  | { type: "trade_completed"; resource_key: string; seq: number; data: TradeOut }
  | { type: "best_bid_updated" | "best_ask_updated"; resource_key: string; seq: number; data: { price: string | null } };

export type MarketWsStatus = "connecting" | "open" | "reconnecting" | "closed";

// The server never sends full order book / trade history state over the
// socket - only this signal, plus incremental deltas afterward. Every
// (re)connect and every subscribe is treated as "state may be stale,
// go re-fetch," matching the backend's documented design.
export function useMarketSocket(resourceKey: string | null, onEvent: (event: MarketWsEvent) => void) {
  const [status, setStatus] = useState<MarketWsStatus>("connecting");
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!resourceKey) return;

    let socket: WebSocket | null = null;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cleanedUp = false;

    const connect = () => {
      setStatus(attempt === 0 ? "connecting" : "reconnecting");
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        attempt = 0;
        setStatus("open");
        socket?.send(JSON.stringify({ type: "subscribe", resource_key: resourceKey }));
      };

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as MarketWsEvent | { type: "ping" };
        if (message.type === "ping") {
          socket?.send(JSON.stringify({ type: "pong" }));
          return;
        }
        onEventRef.current(message);
      };

      socket.onclose = () => {
        if (cleanedUp) return;
        setStatus("reconnecting");
        // Exponential backoff, capped, so a persistently-down backend
        // doesn't spin the client into a reconnect storm.
        const delay = Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      cleanedUp = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
      setStatus("closed");
    };
  }, [resourceKey]);

  return status;
}
