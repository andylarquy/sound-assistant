"""Minimal state-sync broadcaster. On every mutation the API pushes a full
state snapshot to connected clients over a websocket so the UI updates
without polling. Good enough for MVP0's single-user scale; a diff/event
based protocol is a later refinement (see docs/status.md)."""
from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger("sound_assistant.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        stale = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()
