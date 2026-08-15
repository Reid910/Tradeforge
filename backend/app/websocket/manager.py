import asyncio
import itertools
from typing import Any

from fastapi import WebSocket


class MarketConnectionManager:
    """In-memory pub/sub for /ws/market, scoped per resource so a client
    subscribed to Steel never sees Copper Ore events (no full-broadcast).
    Single-process only - no Redis in v1 (see TODO.md), so this only
    works with a single backend instance.

    Sync service code (plain SQLAlchemy, no async) publishes events via
    `publish`, which hops onto the event loop captured at startup via
    `bind_loop`. This lets market_service call it as the very next line
    after `db.commit()` even though it's running in FastAPI's sync-route
    threadpool, not the event loop thread - keeping Postgres as the
    source of truth and the broadcast strictly commit-then-notify.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._seq = itertools.count(1)

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, resource_key: str, websocket: WebSocket) -> None:
        self._subscriptions.setdefault(resource_key, set()).add(websocket)

    def unsubscribe(self, resource_key: str, websocket: WebSocket) -> None:
        sockets = self._subscriptions.get(resource_key)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            self._subscriptions.pop(resource_key, None)

    def drop_connection(self, websocket: WebSocket) -> None:
        for resource_key in list(self._subscriptions.keys()):
            self.unsubscribe(resource_key, websocket)

    def publish(self, resource_key: str, event_type: str, data: dict[str, Any]) -> None:
        """Sync entrypoint - safe to call from plain `def` routes/services.
        Fire-and-forget best-effort delivery on top of Postgres, which
        stays authoritative regardless of whether this ever reaches a
        client (a missed event is caught by the client's periodic REST
        polling / reconnect snapshot, not just the WS stream).
        """
        if self._loop is None:
            return
        message = {"type": event_type, "resource_key": resource_key, "seq": next(self._seq), "data": data}
        asyncio.run_coroutine_threadsafe(self._broadcast(resource_key, message), self._loop)

    async def _broadcast(self, resource_key: str, message: dict[str, Any]) -> None:
        for websocket in list(self._subscriptions.get(resource_key, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 - one dead/misbehaving socket must not break delivery to the rest
                self.drop_connection(websocket)


manager = MarketConnectionManager()
