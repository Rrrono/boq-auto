"""Compatibility wrapper for layered config loading."""

from __future__ import annotations

from src.config_loader import load_config, merge_cli_overrides

__all__ = ["load_config", "merge_cli_overrides"]
