"""SQLite persistence for the control plane (DESIGN.md section 19: SQLite
initially, PostgreSQL later if needed)."""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = os.environ.get("SOUND_ASSISTANT_DB", "sound_assistant.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    # Import models so they're registered on SQLModel.metadata before create_all.
    from server import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
