# Tradeforge — Development TODO

Browser-based incremental factory/economy game: players explore a node map, run mines, process raw materials into products, and trade through a shared real-time market. Built as a portfolio piece — the emphasis is backend architecture, DB design, WebSockets, transactional correctness, testing, and deployment, not content volume.

## Stack

| Layer | Choices |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand, React Flow, Recharts |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic, native WebSockets, Pytest |
| DB | PostgreSQL (decimal types for currency/prices — never float) |
| Infra | Docker, Docker Compose, Caddy, Cloudflare Tunnel, GitHub Actions |

No Redis in v1. Only add it if cross-process WS broadcast, caching, distributed locks, or background queues become a real need.

## MVP loop

- [x] Register / log in
- [x] View generated node map
- [x] Unlock a mining node
- [x] Collect resources from a mine — fully automatic, no click required (see Phase 7)
- [x] Upgrade mine output (backend endpoint exists and works; no dedicated upgrade button in the UI yet)
- [x] Process raw materials → intermediates — place a Furnace, connect it (or don't, for a 1-machine chain), feed it coal + copper ore, watch Copper Ingot show up in Inventory automatically
- [x] Manufacture a finished product — only intermediates exist so far (no multi-stage chain into a "finished" tier yet), but the mechanism is proven end to end
- [ ] List materials/products on the market
- [ ] Get live market updates over WebSocket
- [ ] Reinvest profit into more nodes/upgrades

**Explicitly out of scope for v1:** combat, guilds, direct player-to-player trades, conveyor-belt sim, worker management, deep crafting trees, Redis, multiple backend instances, infinite maps, auctions, equipment, chat, friends lists, leaderboards, multi-currency, mobile app.

---

## Phase 1 — Repo & Docker

- [x] Scaffold `frontend/`, `backend/` (`caddy/`, `scripts/` not needed yet)
- [x] `docker-compose.yml` (dev), `.env.example`, `.gitignore` (`docker-compose.prod.yml` later, at Phase 17)
- [ ] Services: frontend, backend, postgres ✅ — caddy, cloudflared not added yet
- [x] Hot reload for Next.js and FastAPI in dev
- [x] Named volume for Postgres; **not** exposed publicly
- [x] Inter-service comms via Docker service names, not localhost
- [x] Restart policies + health checks; backend waits on Postgres healthcheck
- [ ] Caddy routes: `/` → Next.js, `/api/*` → FastAPI, `/ws/*` → FastAPI WS
- [ ] Cloudflare Tunnel exposes Caddy (no port forwarding)

## Phase 2 — Backend foundation

- [ ] `backend/app/{api,core,db,models,schemas,services,websocket,tests}` + `main.py` — have api/core/db/models/schemas/services; no websocket/tests yet
- [x] Settings/env config, DB connection + session management, Alembic migrations
- [ ] Structured logging, central error handling ⬅ not done yet; CORS ✅, request validation ✅ (pydantic)
- [x] `GET /api/health`, `GET /api/version`

## Phase 3 — Auth

Passwordless by design decision — no password field on `User` at all, not just "not required." Two ways in: email magic link, or an instant guest account.

- [x] Email magic-link sign-in (single-use, 15min-expiry token; account auto-created on first confirm) + guest accounts; session via JWT in an HTTP-only cookie
- [x] Logout, current-user endpoint, protected-route dependency
- [x] Rate limiting on magic-link requests (in-memory; move to Redis if ever multi-instance)
- [x] `POST /api/auth/magic-link`, `POST /api/auth/magic-link/confirm`, `POST /api/auth/guest`, `POST /api/auth/logout`, `GET /api/auth/me`
- [x] `/login` (email + guest), `/auth/confirm` (consumes the magic-link token) pages
- [ ] Real email delivery (SMTP/SES/Resend) before deploying — dev mode currently returns the link directly in the API response instead of sending it

## Phase 4 — Core models

- [x] `User` — id, username, email (nullable, for guests), is_guest, balance, timestamps (no password field — passwordless by design, see Phase 3)
- [x] `MagicLinkToken` — id, email, token, expires_at, used_at, created_at
- [x] `ResourceDefinition` — id, key, name, category, base_value, rarity, icon, yield_amount, tradable
- [x] `InventoryItem` — id, user_id, resource_id, quantity, reserved_quantity, updated_at
- [x] `MapNode` — id, user_id, node_key, resource_id, status, created_at (leaner than originally sketched: no per-user x/y or node_type — positions are computed client-side from a shared static edge template, since the map isn't procedurally generated yet)
- [x] `Mine` — id, user_id, map_node_id, resource_id, level, storage_capacity, stored_quantity, last_collected_at, created_at (`cycle_duration` and `active` dropped: cycle length is derived from `level` via a pure function instead of stored, and there's no "inactive mine" state yet)
- [x] `MachineDefinition` / `MachineDefinitionInput` — replaces the originally sketched `Recipe`/`RecipeInput`: key, name, icon, output resource+qty, inputs (resource+qty each). No `duration` field — production duration is the shared global tick, not per-recipe
- [x] `FactoryGrid` — id, user_id, slot_index, width, height, last_settled_at, created_at
- [x] `Machine` — id, user_id, grid_id, machine_definition_id, x, y, created_at (replaces the originally sketched `ProductionJob`: there's no job queue, a placed machine just produces continuously as long as it's fed)
- [x] `MachineConnection` — id, grid_id, source_machine_id, target_machine_id, created_at (unique on both FK columns — enforces linear chains at the schema level)
- [ ] `MarketOrder` — id, user_id, resource_id, side (buy/sell), price, original/remaining_quantity, status, timestamps
- [ ] `Trade` — id, resource_id, buyer_id, seller_id, buy_order_id, sell_order_id, quantity, price, total_value, created_at
- [ ] `RareDropLog` — id, user_id, mine_id, resource_id, cycle_number, drop_table_version, quantity, generated_at
- [x] All currency/price columns use `Numeric`, never float

## Phase 5 — Seed data

- [x] Raw: Iron Ore, Copper Ore, Coal, Silica
- [x] Rare: Charged Crystal, Prismatic Core (fixed drop rates — upgrades never touch rare odds)
- [ ] Intermediate: Steel, Copper Wire, Glass
- [ ] Finished: Electric Motor, Mining Drill, Control Module
- [ ] Recipes:
  - Iron Ore + Coal → Steel
  - Copper Ore → Copper Wire
  - Silica → Glass
  - Steel + Copper Wire → Electric Motor
  - Steel + Electric Motor → Mining Drill
  - Copper Wire + Glass + Charged Crystal → Control Module
- [ ] Mining Drills feed back into mine upgrades (closes the loop)

## Phase 6 — Node map

- [x] React Flow map: locked / discovered / unlocked states, resource, yield. Design call after Phase 7 landed: this page stays discovery/unlock-only on purpose — mine level, production, and stored amounts are deliberately **not** shown here, since production is fully automatic and belongs on the Inventory page instead. `mine_id` is still embedded in each node for a possible future upgrade button on this page
- [x] Hover node → details panel (design call: hover instead of click, click is reserved for unlocking); unlock only adjacent, discovered nodes
- [ ] Server-generated, deterministic per map seed; positions persisted — currently one shared static template seeded per-user at registration, positions computed client-side (radial layout), not stored. Revisit if/when maps need to differ per player
- [x] Scope: 10–15 nodes, 4 common resources, 1–2 rare nodes, 1 starting node, a few branches
- [x] `GET /api/map`, `POST /api/map/nodes/{id}/unlock` — no separate `GET /api/map/nodes/{id}`, not needed since the full map response already includes every node

## Phase 7 — Mine production (timestamp-based, no per-mine loop, fully automatic)

Design call: no click-to-collect anywhere. Production piles up on its own and lands directly in inventory — the node map's job is purely discovery/unlocking (see Phase 6), not a place to watch numbers tick. All mines share **one global tick grid** rather than each running its own clock, so everything advances in lockstep instead of drifting out of phase depending on when each mine was created.

- [x] Mine auto-created (level 1) when its node is unlocked, snapped onto the shared tick grid at creation (`mine_service._tick_boundary`) so it's in sync with every other mine from the start
- [x] **No collect endpoint.** Instead, `GET /api/map`, `GET /api/mines(/{id})`, and `GET /api/inventory` all depend on `get_current_user_settled` (`api/deps.py`), which auto-credits any production accrued since the user was last seen before the route even runs. This is a deliberate, documented departure from strict REST semantics (a GET has a side effect) in exchange for needing zero background worker and zero player-facing button
- [x] Settlement: whole ticks elapsed since last settle (capped at `mine_max_offline_hours`) → `ticks × yield_amount × level`, storage-capped → credited straight to inventory → `last_collected_at` snapped to the current tick boundary
- [ ] Resolve fixed-chance rare drops server-side, log to `RareDropLog` — **not done**: rare-resource nodes (Charged Crystal, Prismatic Core) currently produce deterministically every tick just like common resources. Real rare-drop-chance mechanics are a separate follow-up
- [x] Server-authoritative time; client never supplies production values
- [x] Idempotent by construction (settling twice in a row with no elapsed tick credits nothing the second time); max offline-accumulation cap (`mine_max_offline_hours`, default 24h)
- [ ] Automated tests — verified manually via curl (tick math, cross-mine sync with mines created seconds apart, offline cap, cross-user ownership 404s) but no Pytest suite yet; that's Phase 15
- [x] `POST /api/mines/{id}/upgrade`, `GET /api/mines/{id}`, `GET /api/mines` (list), `mine_id` embedded in `GET /api/map` node entries for future upgrade UI on the map page
- [x] Upgrades increase output-per-tick and storage capacity — **never** tick speed (that's shared/fixed for everyone) and never rare-drop chance; free for now since there's no currency sink until the market exists (Phase 10)

## Phase 8 — Inventory

This is where automation actually surfaces to the player — "how much have I collected," full stop.

- [x] Basic table: icon, name, category, quantity, reserved qty — plain Tailwind for now, not shadcn/ui yet (that's Phase 13, once the rest of the app shell gets built)
- [x] Polls every 6s (matching the backend tick) so totals visibly climb while sitting on the page, with zero action from the player
- [ ] Filter by category, search by name, sort by qty/rarity
- [ ] Link to recipes and market from item detail
- [x] `GET /api/inventory`
- [x] All mutations go through backend services + DB transactions — `credit_inventory()` in `inventory_service.py`, row-locked, no direct writes from routes

## Phase 9 — Factory production

Design pivot from the original plan: not a recipe-list-and-job-queue page. Instead, a spatial grid where you place machines and connect them into a production chain — coal + copper ore → furnace → copper ingot → inventory. Same automatic, no-click philosophy as mines (Phase 7), and everything shares the *same* global tick as mines, not its own clock.

- [x] `FactoryGrid` (fixed 5×5), one auto-created per user at registration; additional grids unlockable by spending resources (`POST /api/factory/grids/unlock`, costs `factory_grid_unlock_cost_amount` of `factory_grid_unlock_cost_resource_key` — currently 50 Iron Ore; no currency exists yet so this is resource-gated like mine upgrades are free)
- [x] `MachineDefinition` (seed data): fixed recipe per machine type. Just one so far — **Furnace**: Coal + Copper Ore → Copper Ingot. Adding more types is just a seed-data entry, the engine is generic
- [x] `Machine` placed at (x, y) on a grid; `MachineConnection` links one machine's output to another's input
- [x] **Linear chains only, enforced at the DB level**: `MachineConnection` has a unique constraint on both `source_machine_id` and `target_machine_id`, so a machine can have at most one outgoing and one incoming connection — no branch/merge graphs possible, by construction, not by application-level validation
- [x] Cycle prevention at connect-time (`_would_create_cycle`): walks forward from the proposed target to check it doesn't loop back to the proposed source, rejected with 400 before it can ever be created
- [x] Production: same lazy, tick-based settlement pattern as mines, wired into the same `get_current_user_settled` dependency. A chain's head machine pulls inputs from inventory; intermediates flow machine-to-machine without touching inventory; the tail machine's output credits inventory. Run count per settle = `min(elapsed_ticks, affordable_runs_from_current_inventory)` — a starved chain produces nothing and is **not** banked for later, same principle as the mine offline cap, so restocking after a long gap doesn't trigger unbounded catch-up
- [x] `GET /api/factory/definitions`, `GET /api/factory/grids`, `POST /api/factory/grids/unlock`, `POST /api/factory/grids/{id}/machines`, `DELETE /api/factory/machines/{id}`, `POST /api/factory/connections`, `DELETE /api/factory/connections/{id}`
- [x] Verified via curl with tight timing: mines and factory settle on identical elapsed-tick counts, confirming the shared clock actually holds in practice, not just in theory
- [x] Frontend grid-placement UI: React Flow canvas at `/factory`, palette to pick a machine type then click an empty cell to place it, drag between machine handles to connect (native React Flow `onConnect`), select + Delete key to remove a machine or connection. Every cell (empty or occupied) is a node so placement and machines share one coordinate system
- [x] Deliberately minimal on this page: no live-ticking numbers per machine, no "producing/idle" status — this is the *planning* surface (where do things go, how are they wired), production totals surface entirely on Inventory, matching the same design call made for the map page after mine production shipped
- [x] Shared `<Nav>` component across map/factory/inventory now that there are three pages worth cross-linking, replacing the ad hoc single link each page had before
- [ ] Automated tests — verified manually via curl (production math, cycle rejection, duplicate-connection rejection, cross-user ownership, out-of-bounds/occupied-cell placement) but no Pytest suite yet; Phase 15

## Phase 10 — Market order book

- [ ] Limit buy/sell orders: create, cancel, list
- [ ] Matching: best price, then earliest creation time; partial fills supported
- [ ] Reserve seller inventory and buyer currency on order creation; release on cancel
- [ ] Permanent trade-history records
- [ ] Match sequence inside a DB transaction: lock both orders → confirm remaining qty/reserves → compute fill → transfer inventory + currency → deduct fee → update remaining qty → close filled orders → write trade → commit → **then** publish WS event
- [ ] Row locking to prevent duplicate/concurrent execution
- [ ] Configurable transaction fee
- [ ] `GET /api/market/resources/{id}/orders`, `GET /api/market/resources/{id}/trades`, `POST /api/market/orders`, `DELETE /api/market/orders/{id}`, `GET /api/market/my-orders`

## Phase 11 — WebSocket market updates (`/ws/market`)

- [ ] Client → server: `subscribe`/`unsubscribe` with `resourceId`
- [ ] Server → client: `order_created`, `order_updated`, `order_cancelled`, `trade_completed`, `best_bid_updated`, `best_ask_updated`, `market_snapshot_required`, `ping`/`pong`
- [ ] Authenticated connections; per-resource subscription tracking; no full-broadcast
- [ ] Clean up disconnected clients; heartbeat
- [ ] Frontend auto-reconnect with exponential backoff + fresh REST snapshot on reconnect
- [ ] Postgres is the source of truth — commit before broadcast, never the other way around
- [ ] Event IDs/sequence numbers; duplicate events are safely ignorable
- [ ] Never dump full game state into a single WS message

## Phase 12 — Market UI

- [ ] Resource selector, current inventory/balance, best bid/ask
- [ ] Buy/sell order tables, recent trades, order create/cancel dialogs
- [ ] Live WS updates + connection status indicator
- [ ] Price history + volume charts (Recharts)
- [ ] Open-orders list
- [ ] UI clearly separates available vs. reserved inventory, and available vs. reserved currency

## Phase 13 — App shell & nav

- [ ] Sections: Dashboard, Mining Map, Factory, Inventory, Market, Statistics, Settings
- [ ] shadcn sidebar, cards, dialogs, tables, tabs, dropdowns, tooltips, toasts, skeletons, alert dialogs, form validation
- [ ] Visual direction: industrial, dark, clean dashboard, clear rarity indicators, minimal animation, responsive desktop-first

## Phase 14 — Security & validation

- [ ] Password hashing, secure cookies/tokens, ownership checks, rate limiting
- [ ] Caps on order quantity/price, WS subscription count, WS message validation
- [ ] Server-authoritative time and RNG everywhere it matters
- [ ] Transaction-safe inventory + market matching
- [ ] Env-based secrets; DB and (if added later) Redis never exposed; HTTPS via Cloudflare
- [ ] Audit log for economy-affecting actions
- [ ] Never trust client-submitted: resource quantities, mine production, RNG results, balances, upgrade costs, order ownership, production completion

## Phase 15 — Testing

**Backend unit:** mine production math, offline accumulation, storage limits, upgrade math, rare-drop resolution, recipe validation, inventory reservations, production completion, order matching, partial fills, cancellation, fees, insufficient currency/inventory, concurrent submissions, duplicate requests, authz failures

**API integration:** register → unlock mine → collect → manufacture → list on market → second user buys → verify both inventories/balances

**Frontend (Playwright):** register/login, node unlock, mine collection, production flow, order create/cancel, live market updates, WS reconnection

## Phase 16 — Observability

- [ ] Structured logs + request IDs, error logging
- [ ] WS connection/subscription counts, market-order and trade-volume metrics
- [ ] DB and container health checks, basic admin diagnostics page
- [ ] No private user data in logs
- [ ] Later, optional: Prometheus + Grafana

## Phase 17 — Deployment

- [ ] Prod builds for Next.js + FastAPI, persistent Postgres volume
- [ ] Cloudflare Tunnel + Caddy routing, auto-restart, sleep disabled on host
- [ ] Nightly `pg_dump` → compressed → copied off-host (host-only backup is not sufficient)
- [ ] Restore instructions, log rotation, env secrets, health checks
- [ ] GitHub Actions test pipeline
- [ ] Postgres stays private inside the Docker network; Cloudflare exposes only the app

## Phase 18 — README

- [ ] Overview, screenshots, live demo link, architecture diagram
- [ ] Stack, gameplay loop, WS design, market transaction design, DB model overview
- [ ] Docker/local dev setup, env vars, test instructions
- [ ] Deployment architecture, security decisions, known limitations, future improvements

## Phase 19 — Portfolio-ready checklist

- [ ] Register/login works end to end
- [ ] Node map functional; mines produce over time
- [ ] Rare drops use fixed server-side probabilities, unaffected by upgrades
- [ ] Mines upgradeable; inventory persistent
- [ ] Recipes/production jobs work; market supports create/cancel/partial fills
- [ ] Trades are transaction-safe; market updates over WS
- [ ] Client recovers cleanly from WS disconnects
- [ ] Runs via Docker Compose, reachable via Cloudflare Tunnel
- [ ] DB backed up off-host; core systems have automated tests running in CI
- [ ] README explains architecture and tradeoffs; live demo available; nothing visibly half-built

---

## Later (post-MVP, not now)

Redis · multiple backend instances · infinite map generation · guilds · direct P2P trades · auctions · worker characters · equipment · machine-placement grids · conveyor belts · seasonal resets · mobile app · chat · friends lists · leaderboards · multi-currency · speculative market mechanics · large resource/recipe counts · real-time mine simulation
