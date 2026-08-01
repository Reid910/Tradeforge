import type { MineOut } from "@/lib/api";

/**
 * Client-side *display* projection of what a mine currently holds. The
 * server is still the source of truth - this just extrapolates using the
 * cycle_seconds/yield_amount the server already computed, purely so the UI
 * can show progress ticking up between collects instead of a static number.
 * The actual collected amount always comes from the collect response.
 */
export function estimateStored(mine: MineOut, nowMs: number): number {
  const lastCollectedMs = new Date(mine.last_collected_at).getTime();
  const elapsedSeconds = Math.max(0, (nowMs - lastCollectedMs) / 1000);
  const cycles = Math.floor(elapsedSeconds / mine.cycle_seconds);
  const produced = cycles * mine.resource.yield_amount;
  return Math.min(mine.stored_quantity + produced, mine.storage_capacity);
}
