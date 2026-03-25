"""Database release snapshot helpers for admin vs production app modes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
from typing import Any

from src.audit_logger import log_event
from src.cost_schema import schema_database_path
from src.utils import ensure_parent


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


@dataclass(slots=True)
class ReleaseRecord:
    """One released production database snapshot."""

    release_id: str
    path: str
    created_at: str
    created_by: str
    notes: str = ""
    source_path: str = ""
    is_current: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "release_id": self.release_id,
            "path": self.path,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "notes": self.notes,
            "source_path": self.source_path,
            "is_current": self.is_current,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any], current_path: str = "") -> "ReleaseRecord":
        path = str(payload.get("path") or "")
        return cls(
            release_id=str(payload.get("release_id") or ""),
            path=path,
            created_at=str(payload.get("created_at") or ""),
            created_by=str(payload.get("created_by") or ""),
            notes=str(payload.get("notes") or ""),
            source_path=str(payload.get("source_path") or ""),
            is_current=path == current_path,
        )


def release_dir(config: Any) -> Path:
    path = Path(str(config.get("database_release.release_dir", "database/releases")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def master_database_path(config: Any) -> Path:
    return Path(
        str(
            config.get(
                "database_release.master_database_path",
                config.get("ui.default_database_path", "database/qs_database.xlsx"),
            )
        )
    )


def fallback_production_database_path(config: Any) -> Path:
    return Path(
        str(
            config.get(
                "database_release.production_database_path",
                config.get("ui.default_database_path", "database/qs_database.xlsx"),
            )
        )
    )


def release_registry_path(config: Any) -> Path:
    return Path(str(config.get("database_release.metadata_path", str(release_dir(config) / "releases.json"))))


def current_release_pointer_path(config: Any) -> Path:
    return Path(str(config.get("database_release.current_pointer_path", str(release_dir(config) / "current_release.json"))))


def _load_registry(config: Any) -> dict[str, Any]:
    registry_path = release_registry_path(config)
    if not registry_path.exists():
        return {"current_release_path": "", "releases": []}
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload.setdefault("current_release_path", "")
    payload.setdefault("releases", [])
    return payload


def _save_registry(config: Any, registry: dict[str, Any]) -> Path:
    registry_path = release_registry_path(config)
    ensure_parent(registry_path)
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=True), encoding="utf-8")
    pointer_path = current_release_pointer_path(config)
    ensure_parent(pointer_path)
    pointer_path.write_text(
        json.dumps({"current_release_path": registry.get("current_release_path", "")}, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return registry_path


def list_releases(config: Any) -> list[ReleaseRecord]:
    registry = _load_registry(config)
    current_path = str(registry.get("current_release_path") or "")
    records = [ReleaseRecord.from_dict(item, current_path=current_path) for item in registry.get("releases", [])]
    return sorted(records, key=lambda item: item.created_at, reverse=True)


def current_production_database_path(config: Any) -> Path:
    registry = _load_registry(config)
    current_raw = str(registry.get("current_release_path") or "").strip()
    current = Path(current_raw).expanduser() if current_raw else None
    if current is not None and current.exists():
        return current
    fallback = fallback_production_database_path(config)
    if fallback.exists():
        return fallback
    return current if current is not None else fallback


def create_release_snapshot(config: Any, operator_name: str, notes: str = "") -> ReleaseRecord:
    source = master_database_path(config)
    audit_log_path = str(config.get("database_release.audit_log_path", "logs/release_audit.jsonl"))
    if not source.exists():
        log_event(
            operator_name,
            "database_release_create_failed",
            {"reason": "master_database_missing", "source_path": str(source), "_audit_log_path": audit_log_path},
        )
        raise FileNotFoundError(f"Master database not found: {source}")

    stamp = _utc_stamp()
    release_id = f"prod_{stamp}"
    destination = release_dir(config) / f"{source.stem}_{release_id}{source.suffix}"
    counter = 2
    while destination.exists():
        release_id = f"prod_{stamp}_{counter:02d}"
        destination = release_dir(config) / f"{source.stem}_{release_id}{source.suffix}"
        counter += 1
    shutil.copy2(source, destination)
    sidecar_source = schema_database_path(source)
    sidecar_destination = schema_database_path(destination)
    if sidecar_source.exists():
        shutil.copy2(sidecar_source, sidecar_destination)

    record = ReleaseRecord(
        release_id=release_id,
        path=str(destination),
        created_at=stamp,
        created_by=operator_name.strip() or "Admin",
        notes=notes.strip(),
        source_path=str(source),
        is_current=True,
    )
    registry = _load_registry(config)
    releases = [item for item in registry.get("releases", []) if str(item.get("path") or "") != str(destination)]
    releases.append(record.to_dict())
    registry["releases"] = releases
    registry["current_release_path"] = str(destination)
    _save_registry(config, registry)
    log_event(
        record.created_by,
        "database_release_created",
        {
            "release_id": record.release_id,
            "path": record.path,
            "source_path": record.source_path,
            "notes": record.notes,
            "sidecar_path": str(sidecar_destination) if sidecar_source.exists() else "",
            "_audit_log_path": audit_log_path,
        },
    )
    return record


def set_current_release(config: Any, release_path: str, operator_name: str, notes: str = "") -> ReleaseRecord:
    selected = Path(release_path)
    audit_log_path = str(config.get("database_release.audit_log_path", "logs/release_audit.jsonl"))
    if not selected.exists():
        log_event(
            operator_name,
            "database_release_select_failed",
            {"reason": "release_not_found", "release_path": str(selected), "_audit_log_path": audit_log_path},
        )
        raise FileNotFoundError(f"Release snapshot not found: {selected}")

    registry = _load_registry(config)
    matched: dict[str, Any] | None = None
    for item in registry.get("releases", []):
        if Path(str(item.get("path") or "")) == selected:
            matched = item
            break
    if matched is None:
        matched = {
            "release_id": selected.stem,
            "path": str(selected),
            "created_at": _utc_stamp(),
            "created_by": operator_name.strip() or "Admin",
            "notes": notes.strip(),
            "source_path": "",
        }
        registry.setdefault("releases", []).append(matched)

    if notes.strip():
        matched["notes"] = notes.strip()
    registry["current_release_path"] = str(selected)
    _save_registry(config, registry)
    record = ReleaseRecord.from_dict(matched, current_path=str(selected))
    log_event(
        operator_name,
        "database_release_selected",
        {
            "release_id": record.release_id,
            "path": record.path,
            "notes": notes.strip() or record.notes,
            "_audit_log_path": audit_log_path,
        },
    )
    return record


def release_summary(config: Any) -> dict[str, Any]:
    current = current_production_database_path(config)
    releases = list_releases(config)
    return {
        "master_database_path": str(master_database_path(config)),
        "current_production_database_path": str(current),
        "release_dir": str(release_dir(config)),
        "release_count": len(releases),
        "current_release_id": next((item.release_id for item in releases if item.is_current), ""),
    }
