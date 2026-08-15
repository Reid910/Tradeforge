import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import decode_access_token
from app.websocket.manager import manager

router = APIRouter()

HEARTBEAT_SECONDS = 30


async def _authenticate(websocket: WebSocket) -> int | None:
    token = websocket.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    return decode_access_token(token)


@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket) -> None:
    user_id = await _authenticate(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                # Heartbeat: nothing received in a while, ping to keep the
                # connection alive and let the client detect a dead pipe.
                await websocket.send_json({"type": "ping"})
                continue

            msg_type = message.get("type")
            resource_key = message.get("resource_key")

            if msg_type == "subscribe" and resource_key:
                manager.subscribe(resource_key, websocket)
                # The client is expected to fetch its own REST snapshot on
                # subscribe/reconnect - the server never dumps full order
                # book / trade history state over the socket, only deltas.
                await websocket.send_json(
                    {"type": "market_snapshot_required", "resource_key": resource_key, "seq": 0, "data": {}}
                )
            elif msg_type == "unsubscribe" and resource_key:
                manager.unsubscribe(resource_key, websocket)
            elif msg_type == "pong":
                continue
    except WebSocketDisconnect:
        pass
    finally:
        manager.drop_connection(websocket)
