from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.api.schemas import DeviceCreate
from server.broadcast import broadcast_state
from server.models import Device
from server.persistence.db import get_session

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
def list_devices(session: Session = Depends(get_session)) -> list[Device]:
    return session.exec(select(Device)).all()


@router.post("")
async def register_device(body: DeviceCreate, session: Session = Depends(get_session)) -> Device:
    """Devices call this on agent startup to announce themselves (and
    again periodically as a heartbeat - see PATCH .../heartbeat)."""
    device = Device(
        name=body.name,
        platform=body.platform,
        agent_endpoint=body.agent_endpoint,
        mode=body.mode,
        status="online",
        last_seen=datetime.now(timezone.utc),
    )
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


@router.delete("/{device_id}")
async def delete_device(device_id: str, session: Session = Depends(get_session)) -> dict:
    device = session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, f"unknown device {device_id!r}")
    session.delete(device)
    session.commit()
    await broadcast_state(session)
    return {"ok": True}
