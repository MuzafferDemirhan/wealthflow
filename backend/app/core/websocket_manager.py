import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by user_id.

    Thread-safe for concurrent sends. Used by the WS endpoint and
    by Celery tasks (via Redis pub/sub bridge in later sprints).
    """

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, list[WebSocket]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(user_id, []).append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        async with self._lock:
            conns = self._connections.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self._connections.pop(user_id, None)

    async def send_to_user(
        self, user_id: uuid.UUID, message: dict
    ) -> None:
        """Send a JSON message to every active connection for a user."""
        payload = json.dumps(message, default=str)
        async with self._lock:
            conns = list(self._connections.get(user_id, []))

        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                conns = self._connections.get(user_id, [])
                for ws in stale:
                    if ws in conns:
                        conns.remove(ws)
                if not conns:
                    self._connections.pop(user_id, None)

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to every connected user."""
        payload = json.dumps(message, default=str)
        async with self._lock:
            all_conns = [
                ws for conns in self._connections.values() for ws in conns
            ]

        for ws in all_conns:
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    @property
    def active_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


manager = ConnectionManager()


async def authenticate_websocket(
    websocket: WebSocket,
) -> Optional[User]:
    """Authenticate a WebSocket connection via token query param."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return None

    claims = decode_token(token)
    if claims is None or claims.get("type") != "access":
        await websocket.close(code=4001)
        return None

    try:
        user_id = uuid.UUID(claims.get("sub"))
    except (TypeError, ValueError):
        await websocket.close(code=4001)
        return None

    db: Session = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            await websocket.close(code=4001)
            return None
        return user
    finally:
        db.close()
