"""Transport abstraction (DESIGN.md section 10).

The control plane expresses intent ("route this source to these sinks").
A transport is responsible for turning that intent into whatever a real
audio backend needs (Snapcast group/stream assignment, an RTP session,
a local loopback, ...). The control plane must never depend on
transport-specific concepts outside of this boundary.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from server.models import Route, Sink, Source


class TransportError(RuntimeError):
    """Raised when a transport fails to apply a routing intent."""


class AudioTransport(ABC):
    name: str

    @abstractmethod
    def start_route(self, route: Route, source: Source, sinks: list[Sink]) -> None:
        """Make `source` audible on all of `sinks`."""

    @abstractmethod
    def stop_route(self, route: Route, sinks: list[Sink]) -> None:
        """Undo whatever start_route did for this route on `sinks`."""

    @abstractmethod
    def set_volume(self, sink: Sink, volume: float) -> None:
        """Set output volume (0.0-1.0) for a single sink, if supported."""

    def status(self) -> dict:
        """Optional transport-level health/debug info."""
        return {"transport": self.name}
