# Tradeforge

A browser-based incremental factory/economy game — explore a node map, run mines that produce automatically over time, chain machines together into production lines, and (soon) trade what you make on a live market.

Built primarily as a **portfolio piece**. The focus is backend architecture, database design, transactional correctness, and a clean git/PR workflow — not content volume or visual polish.

## What's actually playable right now

- Passwordless auth (email magic link or instant guest account)
- A node map you unlock resource nodes on
- Mines that produce automatically on a shared global tick — no clicking, numbers just accrue
- A factory page where you chain machines together (e.g. Furnace → Press) into named, ordered production lines that also run automatically
- A persistent inventory

The market/trading loop, WebSocket live updates, and deployment are not built yet. See [`TODO.md`](TODO.md) for the full phase-by-phase roadmap, including notes on design decisions that were tried and discarded along the way.

## Architecture highlights

A few decisions worth calling out if you're skimming this as a portfolio sample:

- **No background workers, anywhere.** Mines and factory chains use lazy, timestamp-based settlement: every entity stores `last_settled_at`, and any request that touches it (a page load, an API call) computes elapsed ticks and credits production as a side effect before returning. `GET` requests having a side effect is a deliberate, documented departure from strict REST in exchange for needing zero cron jobs or queues.
- **One shared tick grid.** Every producer (mines, factory chains) settles against the same global tick boundary (`core/ticks.py`), so everything advances in lockstep regardless of when it was created, instead of drifting out of phase on independent clocks.
- **Offline accumulation is capped, not banked.** A starved or idle period beyond `max_offline_hours` is forfeited rather than queued, so returning after a long gap doesn't trigger an unbounded catch-up burst.
- **Chain settlement is computed in one batch per tick, not simulated run-by-run.** A factory chain's per-run inventory need is walked once (source each machine's input from the previous machine's output where the type matches, else inventory), then multiplied by however many ticks elapsed — since machines run in lockstep with no buffering between them, that per-run breakdown is identical for every run.
- **Passwordless by design**, not just "optional" — there's no password column on `User` at all.
- **Everything money/resource-related uses row-level locking and `Numeric` types**, never floats, and inventory mutations only ever happen through service-layer helpers, never direct writes from route handlers.

## Stack

| Layer | Choices |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic |
| DB | PostgreSQL |
| Infra | Docker Compose, GitHub Actions CI |

## Project structure

```
backend/
  app/
    api/        FastAPI routers
    core/       config, security, shared tick logic
    db/         session/engine setup
    models/     SQLAlchemy models
    schemas/    Pydantic request/response models
    services/   business logic (settlement, inventory, auth) — routes stay thin
  migrations/   Alembic migrations

frontend/
  app/          Next.js App Router pages (map, factory, inventory, auth)
  components/   shared UI (nav, map nodes)
  lib/          typed API client, auth hook
```

## Running it locally

Requires Docker and Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: [http://localhost:3100](http://localhost:3100)
- Backend API: [http://localhost:8000](http://localhost:8000) (docs at `/docs`)
- Postgres runs in its own container, not exposed to the host

Migrations run automatically on backend startup. Register with a guest account or a magic link — in development, magic links are returned directly in the API response instead of being emailed, so there's no mail server to configure.

### Environment variables

See [`.env.example`](.env.example). Everything has a working development default except `JWT_SECRET`, which should be a long random value outside of local dev.

## Tests

CI (`.github/workflows/ci.yml`) runs on every PR against `main`:

- **Backend:** `ruff` lint, an import-and-wire-up smoke check, and every Alembic migration applied from scratch against a fresh Postgres instance
- **Frontend:** `tsc --noEmit`, lint, and a production build

An automated Pytest/integration suite isn't in place yet (tracked in `TODO.md`, Phase 15) — current backend behavior is verified manually against the running stack as features land.

## Roadmap

Full phase-by-phase plan, including which designs were tried and abandoned and why, lives in [`TODO.md`](TODO.md).
