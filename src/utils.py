"""General utility helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def safe_float(value: Any) -> float | None:
    """Convert a mixed Excel value into float when possible."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def slugify(text: str) -> str:
    """Create a filesystem-friendly slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return cleaned.strip("_") or "output"


def ensure_parent(path: Path) -> None:
    """Create a parent directory if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: Any) -> None:
    """Write JSON with UTF-8 encoding."""
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def truthy(value: Any) -> bool:
    """Interpret common Excel booleans."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "active"}
