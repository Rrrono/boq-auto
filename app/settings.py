"""Runtime settings and secret-aware environment helpers for the web platform."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


def read_secret_value(env_name: str, *, file_suffix: str = "_FILE") -> str:
    """Resolve a value from an env var or a file path env var."""
    direct = os.getenv(env_name, "")
    if direct.strip():
        return direct.strip()
    file_path = os.getenv(f"{env_name}{file_suffix}", "").strip()
    if not file_path:
        return ""
    return Path(file_path).read_text(encoding="utf-8").strip()


@dataclass(slots=True)
class WebPlatformSettings:
    """Runtime configuration for the API/web platform layer."""

    database_url: str
    cloud_sql_connection_name: str
    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: str


def load_settings() -> WebPlatformSettings:
    explicit_database_url = read_secret_value("BOQ_AUTO_DATABASE_URL")
    cloud_sql_connection_name = os.getenv("BOQ_AUTO_CLOUD_SQL_CONNECTION_NAME", "").strip()
    db_name = os.getenv("BOQ_AUTO_DB_NAME", "boq_auto").strip()
    db_user = os.getenv("BOQ_AUTO_DB_USER", "").strip()
    db_password = read_secret_value("BOQ_AUTO_DB_PASSWORD")
    db_host = os.getenv("BOQ_AUTO_DB_HOST", "").strip()
    db_port = os.getenv("BOQ_AUTO_DB_PORT", "5432").strip()

    database_url = explicit_database_url or _build_database_url(
        cloud_sql_connection_name=cloud_sql_connection_name,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        db_host=db_host,
        db_port=db_port,
    )

    return WebPlatformSettings(
        database_url=database_url,
        cloud_sql_connection_name=cloud_sql_connection_name,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        db_host=db_host,
        db_port=db_port,
    )


def _build_database_url(
    *,
    cloud_sql_connection_name: str,
    db_name: str,
    db_user: str,
    db_password: str,
    db_host: str,
    db_port: str,
) -> str:
    if db_user and db_password and cloud_sql_connection_name:
        password = quote_plus(db_password)
        return (
            f"postgresql+psycopg://{db_user}:{password}@/{db_name}"
            f"?host=/cloudsql/{cloud_sql_connection_name}"
        )
    if db_user and db_password and db_host:
        password = quote_plus(db_password)
        return f"postgresql+psycopg://{db_user}:{password}@{db_host}:{db_port}/{db_name}"
    return "sqlite+pysqlite:///./boq_auto_web.db"
