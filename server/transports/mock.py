"""In-memory transport for local development and UI testing without any
real audio backend installed. Lets MVP0's control-plane/UI loop be
exercised end-to-end before Snapcast is wired up."""
from __future__ import annotations

import logging

from server.models import Route, Sink, Source
from server.transports.base import AudioTransport

logger = logging.getLogger("sound_assistant.transports.mock")


class MockTransport(AudioTransport):
    name = "mock"

    def __init__(self) -> None:
        self._active: dict[str, tuple[Source, list[Sink]]] = {}

    def start_route(self, route: Route, source: Source, sinks: list[Sink]) -> None:
        self._active[route.id] = (source, sinks)
        dest = ", ".join(s.name for s in sinks)
        logger.info("route %s: %s -> [%s]", route.id, source.name, dest)

    def stop_route(self, route: Route, sinks: list[Sink]) -> None:
        self._active.pop(route.id, None)
        logger.info("route %s stopped", route.id)

    def set_volume(self, sink: Sink, volume: float) -> None:
        logger.info("sink %s volume -> %.2f", sink.name, volume)

    def status(self) -> dict:
        return {
            "transport": self.name,
            "active_routes": {
                route_id: {"source": src.name, "sinks": [s.name for s in sinks]}
                for route_id, (src, sinks) in self._active.items()
            },
        }
