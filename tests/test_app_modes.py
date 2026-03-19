from pathlib import Path

from src.models import AppConfig
from ui.app_shell import page_labels_for_mode
from ui.helpers import resolve_default_database_path


def test_production_app_hides_admin_training_features() -> None:
    labels = page_labels_for_mode("production")

    assert "Database Tools" not in labels
    assert "Release Management" not in labels
    assert "Admin / Logs" not in labels
    assert "Workspace / Jobs" in labels
    assert "Tender Analysis" in labels
    assert "BOQ Pricing" in labels


def test_admin_app_exposes_training_and_release_features() -> None:
    labels = page_labels_for_mode("admin")

    assert "Manual Ingestion" in labels
    assert "Database Tools" in labels
    assert "Release Management" in labels
    assert "Admin / Logs" in labels


def test_database_path_selection_defaults_by_app_mode(tmp_path) -> None:
    production_db = tmp_path / "database" / "released.xlsx"
    master_db = tmp_path / "database" / "master" / "master.xlsx"
    production_db.parent.mkdir(parents=True, exist_ok=True)
    master_db.parent.mkdir(parents=True, exist_ok=True)
    production_db.write_bytes(b"prod")
    master_db.write_bytes(b"master")

    config = AppConfig(
        data={
            "ui": {"default_database_path": str(production_db)},
            "database_release": {
                "master_database_path": str(master_db),
                "production_database_path": str(production_db),
                "release_dir": str(tmp_path / "database" / "releases"),
                "metadata_path": str(tmp_path / "database" / "releases" / "releases.json"),
                "current_pointer_path": str(tmp_path / "database" / "releases" / "current_release.json"),
            },
        }
    )

    assert resolve_default_database_path(config, "production") == Path(production_db)
    assert resolve_default_database_path(config, "admin") == Path(master_db)
