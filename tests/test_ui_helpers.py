from src.models import AppConfig
from ui.helpers import create_work_dir, get_current_mode_label, summarize_config


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


def test_get_current_mode_label_handles_ai_disabled_and_active_modes() -> None:
    disabled_config = AppConfig(data={"ai": {"enabled": False}})
    enabled_config = AppConfig(data={"ai": {"enabled": True}})

    assert get_current_mode_label(disabled_config, "rule") == "RULE (AI disabled)"
    assert get_current_mode_label(enabled_config, "hybrid") == "HYBRID (fallback active)"
    assert get_current_mode_label(enabled_config, "ai") == "AI (active)"
