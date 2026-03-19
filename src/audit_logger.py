"""Structured append-only audit logging helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any

from src.config import load_config
from src.utils import ensure_parent


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _audit_log_path(details: dict[str, Any]) -> Path:
    configured_path = str(details.get("_audit_log_path") or "").strip()
    if configured_path:
        return Path(configured_path)
    config = load_config()
    return Path(str(config.get("database_release.audit_log_path", "logs/release_audit.jsonl")))


def _json_safe_details(details: dict[str, Any]) -> dict[str, Any]:
    public_details = {key: value for key, value in details.items() if key != "_audit_log_path"}
    return json.loads(json.dumps(public_details, ensure_ascii=True, default=str))


def log_event(user: str, action: str, details: dict) -> None:
    """Append one structured audit event as a JSONL record."""

    record = {
        "timestamp": _utc_now_iso(),
        "user": user.strip() or "system",
        "action": action.strip(),
        "details": _json_safe_details(details),
    }
    log_path = _audit_log_path(details)
    ensure_parent(log_path)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
