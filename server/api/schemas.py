"""Request bodies for the REST API. Kept separate from server/models.py
because these shapes are about what a client is allowed to send, not what
gets persisted (e.g. clients never set a Device's `id` or `status`)."""
from __future__ import annotations

from pydantic import BaseModel

from server.models import DeviceMode, SinkKind, SourceKind


class DeviceCreate(BaseModel):
    name: str
    platform: str
    agent_endpoint: str | None = None
    mode: DeviceMode = DeviceMode.CENTRAL


class SourceCreate(BaseModel):
    name: str
    kind: SourceKind
    transport_ref: str | None = None


class SinkCreate(BaseModel):
    name: str
    kind: SinkKind
    zone_id: str | None = None
    transport_ref: str | None = None


class ZoneCreate(BaseModel):
    name: str


class RouteCreate(BaseModel):
    source_id: str
    sink_ids: list[str] = []
    zone_ids: list[str] = []


class DeviceSyncUpdate(BaseModel):
    enabled: bool
