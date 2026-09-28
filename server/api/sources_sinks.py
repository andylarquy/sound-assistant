from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.api.schemas import SinkCreate, SourceCreate
from server.broadcast import broadcast_state
from server.models import Device, Sink, Source
from server.persistence.db import get_session

router = APIRouter(prefix="/api", tags=["sources & sinks"])


@router.get("/sources")
def list_sources(session: Session = Depends(get_session)) -> list[Source]:
    return session.exec(select(Source)).all()


@router.post("/devices/{device_id}/sources")
async def create_source(
    device_id: str, body: SourceCreate, session: Session = Depends(get_session)
) -> Source:
    """Upserts on (device_id, name) - same reasoning as register_device:
    an agent re-registering its source on every restart shouldn't leave
    a fresh duplicate behind each time."""
    if session.get(Device, device_id) is None:
        raise HTTPException(404, f"unknown device {device_id!r}")
    existing = session.exec(
        select(Source).where(Source.device_id == device_id, Source.name == body.name)
    ).first()
    source = existing or Source(device_id=device_id, name=body.name, kind=body.kind)
    source.kind = body.kind
    source.transport_ref = body.transport_ref
    session.add(source)
    session.commit()
    session.refresh(source)
    await broadcast_state(session)
    return source


@router.get("/sinks")
def list_sinks(session: Session = Depends(get_session)) -> list[Sink]:
    return session.exec(select(Sink)).all()


@router.post("/devices/{device_id}/sinks")
async def create_sink(
    device_id: str, body: SinkCreate, session: Session = Depends(get_session)
) -> Sink:
    if session.get(Device, device_id) is None:
        raise HTTPException(404, f"unknown device {device_id!r}")
    sink = Sink(device_id=device_id, **body.model_dump())
    session.add(sink)
    session.commit()
    session.refresh(sink)
    await broadcast_state(session)
    return sink
