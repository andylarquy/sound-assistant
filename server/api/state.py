from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from server.persistence.db import get_session
from server.state import build_snapshot

router = APIRouter(prefix="/api", tags=["state"])


@router.get("/state")
def get_state(session: Session = Depends(get_session)) -> dict:
    return build_snapshot(session)
