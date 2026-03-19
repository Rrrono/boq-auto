from src.config_loader import load_config, save_local_config


def test_default_load(tmp_path) -> None:
    default_path = tmp_path / "default.yaml"
    default_path.write_text("ai:\n  enabled: false\nmatching:\n  mode: rule\n", encoding="utf-8")

    config = load_config(str(default_path))

    assert config.get("ai.enabled", False) is False
    assert config.get("matching.mode") == "rule"


def test_local_override(tmp_path) -> None:
    default_path = tmp_path / "default.yaml"
    local_path = tmp_path / "local.yaml"
    default_path.write_text("matching:\n  mode: rule\n", encoding="utf-8")
    local_path.write_text("matching:\n  mode: hybrid\n", encoding="utf-8")

    config = load_config(str(default_path))

    assert config.get("matching.mode") == "hybrid"


def test_env_override(monkeypatch, tmp_path) -> None:
    default_path = tmp_path / "default.yaml"
    default_path.write_text("ai:\n  enabled: false\n", encoding="utf-8")
    monkeypatch.setenv("BOQ_AUTO_AI__ENABLED", "true")

    config = load_config(str(default_path))

    assert config.get("ai.enabled") is True


def test_save_local_config_merges_partial_updates(tmp_path) -> None:
    default_path = tmp_path / "default.yaml"
    local_path = tmp_path / "local.yaml"
    default_path.write_text("ai:\n  enabled: false\nmatching:\n  mode: rule\n", encoding="utf-8")
    local_path.write_text("ai:\n  model: text-embedding-3-small\n", encoding="utf-8")

    written = save_local_config({"ai": {"enabled": True}, "matching": {"mode": "hybrid"}}, str(default_path))
    config = load_config(str(default_path))

    assert written == local_path
    assert config.get("ai.enabled") is True
    assert config.get("ai.model") == "text-embedding-3-small"
    assert config.get("matching.mode") == "hybrid"
