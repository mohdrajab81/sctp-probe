"""WebSocket fan-out hub. No dependencies on transport or storage."""
import json
import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

log = logging.getLogger(__name__)


class WsHub:
    def __init__(self) -> None:
        self._subscribers: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._subscribers.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        try:
            self._subscribers.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, event: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        payload = json.dumps(event)
        for ws in list(self._subscribers):
            try:
                await ws.send_text(payload)
            except (WebSocketDisconnect, RuntimeError):
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
