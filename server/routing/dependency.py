"""Holds the process-wide RoutingEngine instance so API routers can depend
on it without constructing a new one (and a new transport connection) per
request. Set once at startup in server/main.py."""
from __future__ import annotations

from server.routing.engine import RoutingEngine

_engine: RoutingEngine | None = None


def set_engine(engine: RoutingEngine) -> None:
    global _engine
    _engine = engine


def get_engine() -> RoutingEngine:
    if _engine is None:
        raise RuntimeError("RoutingEngine not initialized - is the app started via server.main?")
    return _engine
