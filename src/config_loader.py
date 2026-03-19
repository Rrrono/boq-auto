"""Layered configuration loading with safe local and environment overrides."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

from src.models import AppConfig


LOGGER = logging.getLogger("boq_auto")
ENV_PREFIX = "BOQ_AUTO_"


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw) or {}
    return yaml.safe_load(raw) or {}


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _coerce_env_value(value: str) -> Any:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in normalized:
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized


def _env_overrides() -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        path_parts = key[len(ENV_PREFIX):].lower().split("__")
        cursor = overrides
        for part in path_parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path_parts[-1]] = _coerce_env_value(value)
    return overrides


def load_config(path: str | None = None) -> AppConfig:
    """Load base, optional local, and environment overrides."""

    default_path = Path(path) if path else Path("config/default.yaml")
    local_path = default_path.with_name("local.yaml")
    base = _read_config_file(default_path)
    local = _read_config_file(local_path) if local_path.exists() else {}
    env = _env_overrides()
    merged = _merge_dicts(_merge_dicts(base, local), env)
    LOGGER.info("config_loaded | default=%s | local=%s | env_keys=%s", default_path, local_path if local_path.exists() else "", sorted(env.keys()))
    return AppConfig(data=merged)


def save_local_config(updates: dict[str, Any], path: str | None = None) -> Path:
    """Merge partial updates into config/local.yaml without overwriting the whole file."""

    default_path = Path(path) if path else Path("config/default.yaml")
    local_path = default_path.with_name("local.yaml")
    existing_local = _read_config_file(local_path)
    merged = _merge_dicts(existing_local, updates or {})
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(yaml.safe_dump(merged, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return local_path


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
