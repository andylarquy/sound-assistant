"""Thin glue so API routers can push a fresh snapshot after a mutation
without importing FastAPI's websocket machinery directly."""
from __future__ import annotations

from sqlmodel import Session

from server.state import build_snapshot
from server.ws import manager


async def broadcast_state(session: Session) -> None:
    await manager.broadcast({"type": "state", "data": build_snapshot(session)})
