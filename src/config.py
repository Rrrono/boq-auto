"""Configuration loading and override support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import AppConfig


def load_config(path: str | None = None) -> AppConfig:
    """Load YAML or JSON configuration with a built-in default fallback."""
    config_path = Path(path) if path else Path("config/default.yaml")
    if not config_path.exists():
        return AppConfig(data={})

    raw = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        data = yaml.safe_load(raw) or {}
    return AppConfig(data=data)


def merge_cli_overrides(config: AppConfig, overrides: dict[str, Any]) -> AppConfig:
    """Merge flat dotted CLI overrides into nested configuration."""
    merged = dict(config.data)
    for dotted_key, value in overrides.items():
        if value is None:
            continue
        cursor = merged
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    return AppConfig(data=merged)
