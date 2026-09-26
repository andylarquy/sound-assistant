from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.api.schemas import RouteCreate
from server.broadcast import broadcast_state
from server.models import Route
from server.persistence.db import get_session
from server.routing.dependency import get_engine
from server.routing.engine import RoutingEngine, RoutingError

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("")
def list_routes(session: Session = Depends(get_session)) -> list[Route]:
    return session.exec(select(Route)).all()


@router.post("")
async def create_route(
    body: RouteCreate,
    session: Session = Depends(get_session),
    engine: RoutingEngine = Depends(get_engine),
) -> Route:
    try:
        route = engine.create_route(session, body.source_id, body.sink_ids, body.zone_ids)
    except RoutingError as exc:
        raise HTTPException(400, str(exc)) from exc
    await broadcast_state(session)
    return route


@router.delete("/{route_id}")
async def stop_route(
    route_id: str,
    session: Session = Depends(get_session),
    engine: RoutingEngine = Depends(get_engine),
) -> Route:
    try:
        route = engine.stop_route(session, route_id)
    except RoutingError as exc:
        raise HTTPException(404, str(exc)) from exc
    await broadcast_state(session)
    return route
