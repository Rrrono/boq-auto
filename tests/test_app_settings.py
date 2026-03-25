from __future__ import annotations

import tempfile
from pathlib import Path

from app.settings import _build_database_url, load_settings, read_secret_value


def test_build_database_url_for_cloud_sql_socket() -> None:
    url = _build_database_url(
        cloud_sql_connection_name="project:region:instance",
        db_name="boq_auto",
        db_user="boq_auto_user",
        db_password="top secret",
        db_host="",
        db_port="5432",
    )
    assert url.startswith("postgresql+psycopg://boq_auto_user:")
    assert "host=/cloudsql/project:region:instance" in url
    assert "top+secret" in url


def test_build_database_url_for_direct_postgres_host() -> None:
    url = _build_database_url(
        cloud_sql_connection_name="",
        db_name="boq_auto",
        db_user="boq_auto_user",
        db_password="secret",
        db_host="127.0.0.1",
        db_port="5432",
    )
    assert url == "postgresql+psycopg://boq_auto_user:secret@127.0.0.1:5432/boq_auto"


def test_build_database_url_falls_back_to_sqlite() -> None:
    url = _build_database_url(
        cloud_sql_connection_name="",
        db_name="boq_auto",
        db_user="",
        db_password="",
        db_host="",
        db_port="5432",
    )
    assert url == "sqlite+pysqlite:///./boq_auto_web.db"


def test_read_secret_value_from_file(monkeypatch) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
        handle.write("from-file-value\n")
        secret_file = Path(handle.name)

    monkeypatch.delenv("BOQ_AUTO_DB_PASSWORD", raising=False)
    monkeypatch.setenv("BOQ_AUTO_DB_PASSWORD_FILE", str(secret_file))
    assert read_secret_value("BOQ_AUTO_DB_PASSWORD") == "from-file-value"


def test_load_settings_enables_firebase_auth_when_project_is_available(monkeypatch) -> None:
    monkeypatch.delenv("BOQ_AUTO_FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("BOQ_AUTO_FIREBASE_AUTH_ENABLED", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")

    settings = load_settings()

    assert settings.firebase_project_id == "demo-project"
    assert settings.firebase_auth_enabled is True


def test_load_settings_builds_default_allowed_origins(monkeypatch) -> None:
    monkeypatch.delenv("BOQ_AUTO_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")

    settings = load_settings()

    assert "http://127.0.0.1:3000" in settings.allowed_origins
    assert "http://localhost:3000" in settings.allowed_origins
    assert "https://boq-auto-web--demo-project.us-central1.hosted.app" in settings.allowed_origins
