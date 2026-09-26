from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.api.schemas import ZoneCreate
from server.broadcast import broadcast_state
from server.models import Sink, Zone
from server.persistence.db import get_session

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("")
def list_zones(session: Session = Depends(get_session)) -> list[Zone]:
    return session.exec(select(Zone)).all()


@router.post("")
async def create_zone(body: ZoneCreate, session: Session = Depends(get_session)) -> Zone:
    zone = Zone(name=body.name)
    session.add(zone)
    session.commit()
    session.refresh(zone)
    await broadcast_state(session)
    return zone


@router.put("/{zone_id}/sinks/{sink_id}")
async def add_sink_to_zone(
    zone_id: str, sink_id: str, session: Session = Depends(get_session)
) -> Zone:
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(404, f"unknown zone {zone_id!r}")
    sink = session.get(Sink, sink_id)
    if sink is None:
        raise HTTPException(404, f"unknown sink {sink_id!r}")
    sink.zone_id = zone_id
    session.add(sink)
    session.commit()
    session.refresh(zone)
    await broadcast_state(session)
    return zone


@router.delete("/{zone_id}")
async def delete_zone(zone_id: str, session: Session = Depends(get_session)) -> dict:
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(404, f"unknown zone {zone_id!r}")
    session.delete(zone)
    session.commit()
    await broadcast_state(session)
    return {"ok": True}
