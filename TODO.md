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
- [ ] Collect resources from a mine
- [ ] Upgrade mine extraction speed
- [ ] Process raw materials → intermediates
- [ ] Manufacture a finished product
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
- [ ] `InventoryItem` — id, user_id, resource_id, quantity, reserved_quantity, updated_at
- [x] `MapNode` — id, user_id, node_key, resource_id, status, created_at (leaner than originally sketched: no per-user x/y or node_type — positions are computed client-side from a shared static edge template, since the map isn't procedurally generated yet)
- [ ] `Mine` — id, user_id, map_node_id, resource_id, level, cycle_duration, storage_capacity, stored_quantity, last_collected_at, active
- [ ] `Recipe` / `RecipeInput` — output resource+qty, duration, machine_type, inputs
- [ ] `ProductionJob` — id, user_id, recipe_id, quantity, started_at, completes_at, status
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
- [ ] Mining Drills feed back into mine-speed upgrades (closes the loop)

## Phase 6 — Node map

- [x] React Flow map: locked / discovered / unlocked states, resource, yield — mine level/production-rate/stored-resources wait on Phase 7 (mines don't exist yet)
- [x] Hover node → details panel (design call: hover instead of click, click is reserved for unlocking); unlock only adjacent, discovered nodes
- [ ] Server-generated, deterministic per map seed; positions persisted — currently one shared static template seeded per-user at registration, positions computed client-side (radial layout), not stored. Revisit if/when maps need to differ per player
- [x] Scope: 10–15 nodes, 4 common resources, 1–2 rare nodes, 1 starting node, a few branches
- [x] `GET /api/map`, `POST /api/map/nodes/{id}/unlock` — no separate `GET /api/map/nodes/{id}`, not needed since the full map response already includes every node

## Phase 7 — Mine production (timestamp-based, no per-mine loop)

- [ ] On collect: elapsed time → completed cycles → apply storage cap → resolve fixed-chance rare drops server-side → update inventory → update last_collected_at → log rare drops → return summary
- [ ] Server-authoritative time and RNG; client never supplies production/random values
- [ ] Idempotent collection requests; max offline-accumulation cap
- [ ] Tests: elapsed-time math, storage caps, rare-drop probabilities, repeated-collection idempotency
- [ ] `POST /api/mines/{id}/collect`, `POST /api/mines/{id}/upgrade`, `GET /api/mines/{id}`
- [ ] Upgrades affect speed/storage/common output only — never rare-drop chance

## Phase 8 — Inventory

- [ ] shadcn table/cards: icon, name, category, total/available/reserved qty
- [ ] Filter by category, search by name, sort by qty/rarity
- [ ] Link to recipes and market from item detail
- [ ] `GET /api/inventory`
- [ ] All mutations go through backend services + DB transactions — no direct writes from routes

## Phase 9 — Factory production

- [ ] Recipe list: required materials, missing materials, duration
- [ ] Start job → reserve/consume materials safely; block if insufficient inventory
- [ ] Active jobs view with completion timestamps; collect completed (offline-safe, no double collection)
- [ ] `GET /api/recipes`, `GET /api/production/jobs`, `POST /api/production/jobs`, `POST /api/production/jobs/{id}/collect`
- [ ] Timestamp-based completion, not a running worker

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
