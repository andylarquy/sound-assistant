"""Core domain models for the control plane.

These mirror the concepts in DESIGN.md section 5: Device, Source, Sink,
Zone, Route. Kept intentionally small for MVP0 - richer fields (capability
lists, latency stats, permissions) are added in later milestones.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeviceMode(str, Enum):
    CENTRAL = "central"
    LOCAL = "local"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class SourceKind(str, Enum):
    SYSTEM_AUDIO = "system_audio"
    APPLICATION_AUDIO = "application_audio"
    MICROPHONE = "microphone"
    NETWORK = "network"


class SinkKind(str, Enum):
    SPEAKER = "speaker"
    BLUETOOTH = "bluetooth"
    TV = "tv"
    NETWORK = "network"


class RouteStatus(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


class Device(SQLModel, table=True):
    """A physical or virtual machine participating in the audio network."""

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    platform: str  # "windows" | "macos" | "linux" | "android" | "ios"
    mode: DeviceMode = Field(default=DeviceMode.CENTRAL)
    status: DeviceStatus = Field(default=DeviceStatus.OFFLINE)
    agent_endpoint: str | None = None  # host:port the agent can be reached at, if any
    last_seen: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    # Windows-only capability for now (DESIGN.md section 15): route this
    # device's local output through a virtual audio interface + a
    # synced Snapcast client instead of playing the instant original.
    sync_enabled: bool = Field(default=False)

    sources: List["Source"] = Relationship(back_populates="device")
    sinks: List["Sink"] = Relationship(back_populates="device")


class Source(SQLModel, table=True):
    """Anything capable of producing an audio stream."""

    id: str = Field(default_factory=new_id, primary_key=True)
    device_id: str = Field(foreign_key="device.id")
    name: str
    kind: SourceKind
    # Transport-specific handle, e.g. a snapcast stream id. Opaque to the
    # control plane - only the transport implementation interprets it.
    transport_ref: str | None = None

    device: Optional[Device] = Relationship(back_populates="sources")


class Sink(SQLModel, table=True):
    """Anything capable of consuming an audio stream."""

    id: str = Field(default_factory=new_id, primary_key=True)
    device_id: str = Field(foreign_key="device.id")
    name: str
    kind: SinkKind
    zone_id: str | None = Field(default=None, foreign_key="zone.id")
    # Transport-specific handle, e.g. a snapcast client id.
    transport_ref: str | None = None

    device: Optional[Device] = Relationship(back_populates="sinks")
    zone: Optional["Zone"] = Relationship(back_populates="sinks")


class Zone(SQLModel, table=True):
    """A logical grouping of one or more sinks."""

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str

    sinks: List[Sink] = Relationship(back_populates="zone")


class Route(SQLModel, table=True):
    """A connection between a source and one or more sinks."""

    id: str = Field(default_factory=new_id, primary_key=True)
    source_id: str = Field(foreign_key="source.id")
    transport: str = "mock"
    status: RouteStatus = Field(default=RouteStatus.STOPPED)
    created_at: datetime = Field(default_factory=utcnow)
    error: str | None = None


class RouteSink(SQLModel, table=True):
    """Association between a route and the sinks it targets (flattened;
    zones passed at creation time are expanded into their member sinks)."""

    route_id: str = Field(foreign_key="route.id", primary_key=True)
    sink_id: str = Field(foreign_key="sink.id", primary_key=True)
