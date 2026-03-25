from __future__ import annotations

from pathlib import Path

from app.settings import _build_database_url, read_secret_value


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


def test_read_secret_value_from_file(monkeypatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "db_password.txt"
    secret_file.write_text("from-file-value\n", encoding="utf-8")
    monkeypatch.delenv("BOQ_AUTO_DB_PASSWORD", raising=False)
    monkeypatch.setenv("BOQ_AUTO_DB_PASSWORD_FILE", str(secret_file))
    assert read_secret_value("BOQ_AUTO_DB_PASSWORD") == "from-file-value"
