from pathlib import Path

from src.models import AppConfig
from ui.helpers import create_work_dir, summarize_config


def test_create_work_dir_uses_output_root(tmp_path) -> None:
    config = AppConfig(data={"paths": {"output_dir": str(tmp_path)}})
    work_dir = create_work_dir(config)
    assert work_dir.exists()
    assert work_dir.parent == tmp_path / "ui_runs"


def test_summarize_config_returns_expected_sections() -> None:
    config = AppConfig(data={"app": {"log_level": "INFO"}, "paths": {"output_dir": "output"}})
    summary = summarize_config(config)
    assert "app" in summary
    assert "paths" in summary
    assert "database_release" in summary
