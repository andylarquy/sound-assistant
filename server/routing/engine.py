"""Routing engine: the control-plane side of "express intent, not
implementation" (DESIGN.md sections 7 and 23.1).

Callers ask for `source -> [sinks and/or zones]`; this module resolves
zones into their member sinks, persists a Route, and delegates the actual
audio work to whichever AudioTransport is configured.
"""
from __future__ import annotations

from sqlmodel import Session, select

from server.models import Route, RouteSink, RouteStatus, Sink, Source, Zone
from server.transports.base import AudioTransport, TransportError


class RoutingError(RuntimeError):
    pass


class RoutingEngine:
    def __init__(self, transport: AudioTransport) -> None:
        self.transport = transport

    def _resolve_sinks(
        self, session: Session, sink_ids: list[str], zone_ids: list[str]
    ) -> list[Sink]:
        resolved: dict[str, Sink] = {}

        for sink_id in sink_ids:
            sink = session.get(Sink, sink_id)
            if sink is None:
                raise RoutingError(f"unknown sink {sink_id!r}")
            resolved[sink.id] = sink

        for zone_id in zone_ids:
            zone = session.get(Zone, zone_id)
            if zone is None:
                raise RoutingError(f"unknown zone {zone_id!r}")
            for sink in zone.sinks:
                resolved[sink.id] = sink

        if not resolved:
            raise RoutingError("route must have at least one destination sink or zone")

        return list(resolved.values())

    def create_route(
        self,
        session: Session,
        source_id: str,
        sink_ids: list[str] | None = None,
        zone_ids: list[str] | None = None,
    ) -> Route:
        source = session.get(Source, source_id)
        if source is None:
            raise RoutingError(f"unknown source {source_id!r}")

        sinks = self._resolve_sinks(session, sink_ids or [], zone_ids or [])

        route = Route(source_id=source.id, transport=self.transport.name)
        session.add(route)
        session.flush()  # assign route.id before creating RouteSink rows

        for sink in sinks:
            session.add(RouteSink(route_id=route.id, sink_id=sink.id))

        try:
            self.transport.start_route(route, source, sinks)
            route.status = RouteStatus.ACTIVE
        except TransportError as exc:
            route.status = RouteStatus.ERROR
            route.error = str(exc)

        session.add(route)
        session.commit()
        session.refresh(route)
        return route

    def stop_route(self, session: Session, route_id: str) -> Route:
        route = session.get(Route, route_id)
        if route is None:
            raise RoutingError(f"unknown route {route_id!r}")

        try:
            self.transport.stop_route(route)
            route.status = RouteStatus.STOPPED
            route.error = None
        except TransportError as exc:
            route.status = RouteStatus.ERROR
            route.error = str(exc)

        session.add(route)
        session.commit()
        session.refresh(route)
        return route

    def sinks_for_route(self, session: Session, route_id: str) -> list[Sink]:
        rows = session.exec(select(RouteSink).where(RouteSink.route_id == route_id)).all()
        return [session.get(Sink, row.sink_id) for row in rows]
