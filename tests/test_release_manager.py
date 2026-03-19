from pathlib import Path

from src.models import AppConfig
from src.cost_schema import schema_database_path
from src.release_manager import (
    create_release_snapshot,
    current_production_database_path,
    list_releases,
    master_database_path,
    set_current_release,
)


def _config(tmp_path) -> AppConfig:
    return AppConfig(
        data={
            "ui": {"default_database_path": str(tmp_path / "database" / "fallback.xlsx")},
            "database_release": {
                "master_database_path": str(tmp_path / "database" / "master" / "qs_database_master.xlsx"),
                "production_database_path": str(tmp_path / "database" / "fallback.xlsx"),
                "release_dir": str(tmp_path / "database" / "releases"),
                "metadata_path": str(tmp_path / "database" / "releases" / "releases.json"),
                "current_pointer_path": str(tmp_path / "database" / "releases" / "current_release.json"),
                "audit_log_path": str(tmp_path / "logs" / "release_audit.jsonl"),
            },
        }
    )


def test_create_release_snapshot_versions_without_overwriting(tmp_path) -> None:
    config = _config(tmp_path)
    master_path = master_database_path(config)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_bytes(b"master-v1")
    schema_database_path(master_path).write_bytes(b"schema-v1")

    first = create_release_snapshot(config, "Owner", "First release")
    master_path.write_bytes(b"master-v2")
    schema_database_path(master_path).write_bytes(b"schema-v2")
    second = create_release_snapshot(config, "Owner", "Second release")

    assert first.path != second.path
    assert Path(first.path).exists()
    assert Path(second.path).exists()
    assert Path(first.path).read_bytes() == b"master-v1"
    assert Path(second.path).read_bytes() == b"master-v2"
    assert schema_database_path(first.path).read_bytes() == b"schema-v1"
    assert schema_database_path(second.path).read_bytes() == b"schema-v2"


def test_current_production_database_defaults_to_latest_release(tmp_path) -> None:
    config = _config(tmp_path)
    master_path = master_database_path(config)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_bytes(b"master")

    created = create_release_snapshot(config, "Owner")

    assert current_production_database_path(config) == Path(created.path)
    assert Path(config.get("database_release.audit_log_path")).exists()


def test_set_current_release_switches_pointer(tmp_path) -> None:
    config = _config(tmp_path)
    master_path = master_database_path(config)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_bytes(b"master-a")
    first = create_release_snapshot(config, "Owner", "A")
    master_path.write_bytes(b"master-b")
    second = create_release_snapshot(config, "Owner", "B")

    set_current_release(config, first.path, "Owner")

    releases = list_releases(config)
    current = next(item for item in releases if item.is_current)
    assert current.path == first.path
    assert Path(second.path).exists()
