"""SQLite persistence for the control plane (DESIGN.md section 19: SQLite
initially, PostgreSQL later if needed)."""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

DB_PATH = os.environ.get("SOUND_ASSISTANT_DB", "sound_assistant.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def _sql_literal(value: object) -> str | None:
    """Render a simple Python scalar as a SQLite literal for use in a
    DEFAULT clause. Returns None for anything not a plain constant (e.g. a
    default_factory), leaving the new column nullable instead of guessing."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def _add_missing_columns() -> None:
    """`create_all()` only creates missing *tables*, never adds columns to
    ones that already exist - so a column added to a model after the DB was
    first created (like Device.sync_enabled) would otherwise 500 on an
    already-deployed database. SQLite's ADD COLUMN is enough for this
    project's scale; reach for a real migration tool if that changes.

    Existing rows get the column's Python-side default via an explicit
    DEFAULT clause - SQLite's bare ADD COLUMN otherwise backfills NULL,
    not the model's declared default, for every row already there."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.tables.values():
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=conn.dialect)
                default_sql = ""
                if column.default is not None and getattr(column.default, "is_scalar", False):
                    literal = _sql_literal(column.default.arg)
                    if literal is not None:
                        default_sql = f" DEFAULT {literal}"
                conn.execute(
                    text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}{default_sql}")
                )


def create_db_and_tables() -> None:
    # Import models so they're registered on SQLModel.metadata before create_all.
    from server import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
