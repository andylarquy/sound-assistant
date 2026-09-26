"""Builds the full state snapshot shared by the REST `/api/state` endpoint
and every websocket broadcast, so the UI always renders from one shape."""
from __future__ import annotations

from sqlmodel import Session, select

from server.models import Device, Route, RouteSink, Sink, Source, Zone


def build_snapshot(session: Session) -> dict:
    devices = session.exec(select(Device)).all()
    sources = session.exec(select(Source)).all()
    sinks = session.exec(select(Sink)).all()
    zones = session.exec(select(Zone)).all()
    routes = session.exec(select(Route)).all()
    route_sinks = session.exec(select(RouteSink)).all()

    sinks_by_route: dict[str, list[str]] = {}
    for rs in route_sinks:
        sinks_by_route.setdefault(rs.route_id, []).append(rs.sink_id)

    return {
        "devices": [d.model_dump(mode="json") for d in devices],
        "sources": [s.model_dump(mode="json") for s in sources],
        "sinks": [s.model_dump(mode="json") for s in sinks],
        "zones": [
            {**z.model_dump(mode="json"), "sink_ids": [s.id for s in z.sinks]} for z in zones
        ],
        "routes": [
            {**r.model_dump(mode="json"), "sink_ids": sinks_by_route.get(r.id, [])}
            for r in routes
        ],
    }
