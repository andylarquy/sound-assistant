"""Control-plane entrypoint (DESIGN.md section 19).

Run with:
    uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

Transport is selected via SOUND_ASSISTANT_TRANSPORT=mock|snapcast
(default: mock, so the UI/API loop works with nothing else installed).
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api import devices, routes, sources_sinks, state, zones
from server.persistence.db import create_db_and_tables, engine
from server.routing.dependency import set_engine
from server.routing.engine import RoutingEngine
from server.transports.base import AudioTransport
from server.transports.mock import MockTransport
from server.transports.snapcast import SnapcastTransport
from server.ws import manager

logging.basicConfig(level=logging.INFO)

UI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "web", "dist")


def build_transport() -> AudioTransport:
    kind = os.environ.get("SOUND_ASSISTANT_TRANSPORT", "mock").lower()
    if kind == "mock":
        return MockTransport()
    if kind == "snapcast":
        host = os.environ.get("SNAPSERVER_HOST", "127.0.0.1")
        port = int(os.environ.get("SNAPSERVER_PORT", "1705"))
        return SnapcastTransport(host=host, port=port)
    raise ValueError(f"unknown SOUND_ASSISTANT_TRANSPORT={kind!r}")


app = FastAPI(title="Sound Assistant control plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router)
app.include_router(sources_sinks.router)
app.include_router(zones.router)
app.include_router(routes.router)
app.include_router(state.router)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    set_engine(RoutingEngine(build_transport()))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # UI doesn't send anything meaningful yet; just keep the
            # connection open and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if os.path.isdir(UI_DIR):
    app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")


_ = engine  # re-exported for convenience (e.g. scripts/shell access to the DB engine)
