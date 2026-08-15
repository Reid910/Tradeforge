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
- [x] List materials/products on the market
- [x] Get live market updates over WebSocket
- [ ] Reinvest profit into more nodes/upgrades — mine upgrades are still free (no currency sink wired up); this is the same open design question flagged in Phase 5 (Mining Drills → upgrades)

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
- [x] `MachineChain` — id, user_id, name, active, last_settled_at, created_at. `Machine` — id, chain_id, machine_definition_id, position, created_at (replaces the originally sketched `ProductionJob` and the earlier standalone `Machine`: ownership/active-state/settlement now live on the chain, a machine is just a definition + its left-to-right position within one)
- [x] `MarketOrder` — id, user_id, resource_id, side (buy/sell), price, original/remaining_quantity, status, timestamps
- [x] `Trade` — id, resource_id, buyer_id, seller_id, buy_order_id, sell_order_id, quantity, price, total_value, created_at (plus `fee`, per Phase 10's configurable transaction fee). `User.reserved_balance` added alongside — the currency-side counterpart to `InventoryItem.reserved_quantity`, needed to reserve a buyer's funds on order creation
- [ ] `RareDropLog` — id, user_id, mine_id, resource_id, cycle_number, drop_table_version, quantity, generated_at
- [x] All currency/price columns use `Numeric`, never float

## Phase 5 — Seed data

- [x] Raw: Iron Ore, Copper Ore, Coal, Silica
- [x] Rare: Charged Crystal, Prismatic Core (fixed drop rates — upgrades never touch rare odds)
- [x] Intermediate: Steel, Copper Wire, Glass
- [x] Finished: Electric Motor, Mining Drill, Control Module
- [x] Recipes:
  - Iron Ore + Coal → Steel (Smelter)
  - Copper Ore → Copper Wire (Wire Drawer)
  - Silica → Glass (Glassworks)
  - Steel + Copper Wire → Electric Motor (Motor Assembler)
  - Steel + Electric Motor → Mining Drill (Drill Press)
  - Copper Wire + Glass + Charged Crystal → Control Module (Control Fabricator)
- [ ] Mining Drills feed back into mine upgrades (closes the loop) — **design decision needed**: `mine_service.upgrade()` is currently free (Phase 7 note: "free for now since there's no currency sink until the market exists"). Making it consume a Mining Drill is a real economy change — does upgrade cost become Mining Drill(s) only, Mining Drill + currency, or does currency (from Phase 10's market) replace this item-sink idea entirely? Left undone pending that call rather than guessed.

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

Went through four real designs before landing here, each one shipped, curl-verified, and then discarded as requirements got clearer - worth knowing if you're reading the git history: (1) a spatial grid with drag-to-connect machines, (2) the same grid but with automatic left-to-right adjacency and click-to-block links, (3) no grid or spatial relationship at all - a machine as an owned instance pulling straight from inventory, no machine-to-machine piping, (4) **what's actually live**: named chains - an ordered, appendable list of machines (no grid, no x/y, just position). Machines still run left to right in lockstep like design (2), but building one is "append to a list" instead of "place and wire on a grid," which is what actually made it phone-friendly - dragging/wiring was the real problem, not the sequencing concept. Same automatic, no-click philosophy as mines (Phase 7), same shared global tick.

- [x] `MachineDefinition` (seed data): fixed recipe per machine type. Two so far — **Furnace** (Coal + Copper Ore → Copper Ingot) and **Press** (Copper Ingot → Copper Plate, a "finished" resource), sized so a Furnace→Press chain runs cleanly (1x output feeds 1x input, no leftover). Adding more is just a seed-data entry
- [x] `MachineChain`: a named, ordered list of machines. `POST /api/factory/chains` to create, `DELETE /api/factory/chains/{id}` to remove (cascades to its machines). `POST /api/factory/chains/{id}/machines` appends a machine to the end; `DELETE /api/factory/chains/{id}/machines/{machine_id}` removes one and closes the position gap
- [x] **Settlement walks the whole chain**, not just the head: the first machine pulls from inventory, each machine after it sources from the previous machine's output where the resource type matches (else falls back to inventory), and only the last machine's output is credited back to inventory - nothing in between ever touches it. Per-run inventory need is computed once per chain (not simulated run-by-run, since there's no cross-run buffering), so N elapsed ticks just multiply out - same batch-settlement shape as mines
- [x] **Active/Paused toggle** (`POST /api/factory/chains/{id}/toggle`), at the chain level: active chains auto-produce every tick, same lazy settlement pattern as mines. Pausing freezes the chain's clock entirely; reactivating resets to "now" rather than counting the whole paused span, so there's no surprise catch-up burst
- [x] **Manual run** (`POST /api/factory/chains/{id}/run`): run one pass through the whole chain on demand. Only allowed while the chain is **paused** — returns 400 otherwise — so a manual run can never race the automatic per-tick settlement of the same chain. All-or-nothing: 400 if the chain can't produce anything this pass
- [x] `GET /api/factory/definitions`, `GET /api/factory/chains`
- [x] Frontend: `/factory` shows chains as cards - name, Active/Paused pill, Run now (disabled while active), Delete chain, and the machines in order as chips (icon + recipe) with a trailing "+ Add machine" menu. Still a responsive flex-wrap list under the hood, nothing that doesn't work with a thumb on a phone
- [x] Deliberately minimal here on purpose, same principle as the map page: no live-ticking numbers, no per-machine production preview. This page is for owning/configuring chains; production totals surface entirely on Inventory
- [x] Shared `<Nav>` component across map/factory/inventory now that there are three pages worth cross-linking
- [ ] Automated tests — verified manually via curl (chain settlement math with a real multi-machine chain, pause/resume freeze-and-reset, manual-run-only-while-paused, affordability checks, cross-user ownership) but no Pytest suite yet; Phase 15

## Phase 10 — Market order book

- [x] Limit buy/sell orders: create, cancel, list
- [x] Matching: best price, then earliest creation time; partial fills supported
- [x] Reserve seller inventory (existing `InventoryItem.reserved_quantity`) and buyer currency (new `User.reserved_balance`) on order creation; release on cancel
- [x] Permanent trade-history records (`trades` table)
- [x] Match sequence inside a DB transaction: lock both orders → confirm remaining qty/reserves → compute fill → transfer inventory + currency → deduct fee → update remaining qty → close filled orders → write trade → commit → **then** publish WS event — everything up to commit is done; the WS publish step is Phase 11
- [x] Row locking to prevent duplicate/concurrent execution (`with_for_update` on the user, inventory item, and both orders involved in each fill)
- [x] Configurable transaction fee (`settings.market_fee_rate`, charged to the seller's proceeds)
- [x] `GET /api/market/resources/{key}/orders`, `GET /api/market/resources/{key}/trades`, `POST /api/market/orders`, `DELETE /api/market/orders/{id}`, `GET /api/market/my-orders` — routes use the resource's string `key`, not a numeric id, matching how every other resource lookup in this codebase works

## Phase 11 — WebSocket market updates (`/ws/market`)

- [x] Client → server: `subscribe`/`unsubscribe` with `resource_key` (string key, not a numeric `resourceId` — matches every other resource lookup in this codebase)
- [x] Server → client: `order_created`, `order_updated`, `order_cancelled`, `trade_completed`, `best_bid_updated`, `best_ask_updated`, `market_snapshot_required`, `ping`/`pong`
- [x] Authenticated connections (session cookie, same JWT as REST); per-resource subscription tracking; no full-broadcast (a `dict[resource_key, set[WebSocket]]` in `MarketConnectionManager`)
- [x] Clean up disconnected clients; heartbeat (30s `receive_json` timeout triggers a `ping`; disconnect drops all of that socket's subscriptions)
- [ ] Frontend auto-reconnect with exponential backoff + fresh REST snapshot on reconnect — deferred to Phase 12, since there's no market UI/WS client yet for it to live in
- [x] Postgres is the source of truth — commit before broadcast, never the other way around (`manager.publish(...)` is only ever called as the line immediately after `db.commit()`)
- [x] Event IDs/sequence numbers; duplicate events are safely ignorable (monotonic `seq` counter per event; server is single-process/in-memory only, per "no Redis in v1")
- [x] Never dump full game state into a single WS message — on `subscribe`, the server sends `market_snapshot_required` (not the book itself) so the client fetches its own REST snapshot; only deltas stream after that

## Phase 12 — Market UI

- [x] Resource selector, current inventory/balance, best bid/ask
- [x] Buy/sell order tables, recent trades, order create/cancel — **forms, not dialogs**: shadcn/ui (which is where a real dialog primitive would come from) isn't installed until Phase 13, and every other page in the app hand-rolls Tailwind rather than using modals for anything (e.g. factory's inline "New chain" form). An inline buy/sell form matches that existing convention; revisit as a modal once Phase 13 lands
- [x] Live WS updates + connection status indicator (`lib/useMarketSocket.ts` — subscribe, handle `market_snapshot_required` by invalidating the REST queries, exponential-backoff auto-reconnect; status dot in the page header, same visual pattern as `BackendStatus`)
- [ ] Price history + volume charts (Recharts) — deferred: not part of the MVP loop checklist, and there's no price-history endpoint yet either (would need one first)
- [x] Open-orders list (with cancel)
- [x] UI clearly separates available vs. reserved inventory, and available vs. reserved currency — required exposing `User.reserved_balance` on `GET /api/auth/me`, which wasn't in `UserOut` yet (added here). Also added `GET /api/market/resources` (list of tradable resources), since nothing existed for the resource selector to query

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
