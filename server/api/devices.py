from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.api.schemas import DeviceCreate, DeviceSyncUpdate
from server.broadcast import broadcast_state
from server.models import Device, Route, RouteSink, Sink, Source
from server.persistence.db import get_session

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
def list_devices(session: Session = Depends(get_session)) -> list[Device]:
    return session.exec(select(Device)).all()


@router.post("")
async def register_device(body: DeviceCreate, session: Session = Depends(get_session)) -> Device:
    """Devices call this on agent startup to announce themselves (and
    again periodically as a heartbeat - see PATCH .../heartbeat).

    Upserts on (name, platform) rather than always inserting - an agent
    restarting (the same physical machine, same hostname-derived name)
    should reuse its existing device, not pile up a fresh duplicate every
    time. Duplicates weren't just a UI annoyance: with the sync toggle,
    each one is a real route target, so restarting the agent a few times
    meant actually hearing the same PC audio multiple times over."""
    existing = session.exec(
        select(Device).where(Device.name == body.name, Device.platform == body.platform)
    ).first()
    device = existing or Device(name=body.name, platform=body.platform)
    device.agent_endpoint = body.agent_endpoint
    device.mode = body.mode
    device.status = "online"
    device.last_seen = datetime.now(timezone.utc)
    session.add(device)
    session.commit()
    session.refresh(device)
    await broadcast_state(session)
    return device


@router.post("/{device_id}/heartbeat")
async def heartbeat(device_id: str, session: Session = Depends(get_session)) -> Device:
    device = session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, f"unknown device {device_id!r}")
    device.status = "online"
    device.last_seen = datetime.now(timezone.utc)
    session.add(device)
    session.commit()
    session.refresh(device)
    await broadcast_state(session)
    return device


@router.put("/{device_id}/sync")
async def set_device_sync(
    device_id: str, body: DeviceSyncUpdate, session: Session = Depends(get_session)
) -> Device:
    """Toggles synced local playback (DESIGN.md section 15) for this
    device. Windows-only for now - it's a capability, not every device
    has it (section 3.3), so anything else is rejected rather than
    silently accepted and ignored."""
    device = session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, f"unknown device {device_id!r}")
    if device.platform != "windows":
        raise HTTPException(400, f"sync toggle is not supported on platform {device.platform!r}")
    device.sync_enabled = body.enabled
    session.add(device)
    session.commit()
    session.refresh(device)
    await broadcast_state(session)
    return device


@router.delete("/{device_id}")
async def delete_device(device_id: str, session: Session = Depends(get_session)) -> dict:
    """Deleting a device also tears down everything that depended on it:
    its sources/sinks, any routes that used them, and the route<->sink
    links for those routes. Source/Sink.device_id are NOT NULL, so a
    plain `session.delete(device)` fails with an IntegrityError the
    moment SQLAlchemy tries to null those out instead of removing them."""
    device = session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, f"unknown device {device_id!r}")

    sources = session.exec(select(Source).where(Source.device_id == device_id)).all()
    sinks = session.exec(select(Sink).where(Sink.device_id == device_id)).all()
    source_ids = [s.id for s in sources]
    sink_ids = [s.id for s in sinks]

    routes = session.exec(select(Route).where(Route.source_id.in_(source_ids))).all() if source_ids else []
    route_ids = {r.id for r in routes}
    if sink_ids:
        route_ids |= {
            rs.route_id
            for rs in session.exec(select(RouteSink).where(RouteSink.sink_id.in_(sink_ids))).all()
        }

    for route_id in route_ids:
        for rs in session.exec(select(RouteSink).where(RouteSink.route_id == route_id)).all():
            session.delete(rs)
        route = session.get(Route, route_id)
        if route is not None:
            session.delete(route)

    for source in sources:
        session.delete(source)
    for sink in sinks:
        session.delete(sink)

    session.delete(device)
    session.commit()
    await broadcast_state(session)
    return {"ok": True}
