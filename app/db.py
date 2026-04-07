"""Database configuration for the BOQ AUTO web platform APIs."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import load_settings
SETTINGS = load_settings()
DATABASE_URL = SETTINGS.database_url
ENGINE_KWARGS = {"future": True, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    ENGINE_KWARGS["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **ENGINE_KWARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base declarative class for ORM models."""


def init_db() -> None:
    """Create tables for the MVP web platform schema."""
    from app import orm_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_review_task_columns()


def _ensure_review_task_columns() -> None:
    """Additive compatibility for newer review-task fields on existing databases."""
    inspector = inspect(engine)
    if "review_tasks" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("review_tasks")}
    column_definitions = {
        "matched_item_code": "VARCHAR(128) NOT NULL DEFAULT ''",
        "promotion_target": "VARCHAR(64) NOT NULL DEFAULT ''",
        "promotion_status": "VARCHAR(64) NOT NULL DEFAULT 'pending'",
        "feedback_action": "VARCHAR(32) NOT NULL DEFAULT ''",
        "feedback_logged_at": "TIMESTAMP NULL",
    }

    with engine.begin() as connection:
        for column_name, sql_definition in column_definitions.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE review_tasks ADD COLUMN {column_name} {sql_definition}"))


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
