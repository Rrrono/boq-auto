"""Disk-backed job state models for the Streamlit workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from src.utils import ensure_parent


def utc_now_iso() -> str:
    """Return a stable UTC timestamp string."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class JobArtifactVersion:
    """One persisted version of a generated artifact."""

    version_id: str
    path: str
    status: str
    created_at: str = field(default_factory=utc_now_iso)
    created_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "path": self.path,
            "status": self.status,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobArtifactVersion":
        return cls(
            version_id=str(payload.get("version_id") or ""),
            path=str(payload.get("path") or ""),
            status=str(payload.get("status") or "completed"),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            created_by=str(payload.get("created_by") or ""),
        )


@dataclass(slots=True)
class JobArtifact:
    """Tracked output or intermediate artifact for a workspace job."""

    artifact_id: str
    artifact_type: str
    label: str
    action: str
    latest_path: str
    latest_status: str = "completed"
    latest_created_at: str = field(default_factory=utc_now_iso)
    latest_created_by: str = ""
    versions: list[JobArtifactVersion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "label": self.label,
            "action": self.action,
            "latest_path": self.latest_path,
            "latest_status": self.latest_status,
            "latest_created_at": self.latest_created_at,
            "latest_created_by": self.latest_created_by,
            "versions": [version.to_dict() for version in self.versions],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobArtifact":
        latest_path = str(payload.get("latest_path") or payload.get("path") or "")
        latest_status = str(payload.get("latest_status") or payload.get("status") or "completed")
        latest_created_at = str(payload.get("latest_created_at") or payload.get("created_at") or utc_now_iso())
        latest_created_by = str(payload.get("latest_created_by") or payload.get("created_by") or "")
        versions_payload = payload.get("versions") or []
        versions = [JobArtifactVersion.from_dict(item) for item in versions_payload]
        if not versions and latest_path:
            versions = [
                JobArtifactVersion(
                    version_id="v1",
                    path=latest_path,
                    status=latest_status,
                    created_at=latest_created_at,
                    created_by=latest_created_by,
                )
            ]
        return cls(
            artifact_id=str(payload.get("artifact_id") or ""),
            artifact_type=str(payload.get("artifact_type") or ""),
            label=str(payload.get("label") or ""),
            action=str(payload.get("action") or ""),
            latest_path=latest_path,
            latest_status=latest_status,
            latest_created_at=latest_created_at,
            latest_created_by=latest_created_by,
            versions=versions,
        )


@dataclass(slots=True)
class JobState:
    """Persistent job metadata and file references."""

    job_id: str
    title: str
    region: str
    created_at: str
    job_dir: str
    inputs: dict[str, str] = field(default_factory=dict)
    artifacts: list[JobArtifact] = field(default_factory=list)
    status: dict[str, Any] = field(default_factory=dict)
    operator_name: str = ""
    last_modified_by: str = ""
    last_modified_at: str = ""
    archived: bool = False
    archived_at: str = ""
    archived_by: str = ""
    action_history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def state_path(self) -> Path:
        return Path(self.job_dir) / "state.json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "region": self.region,
            "created_at": self.created_at,
            "job_dir": self.job_dir,
            "inputs": dict(self.inputs),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "status": dict(self.status),
            "operator_name": self.operator_name,
            "last_modified_by": self.last_modified_by,
            "last_modified_at": self.last_modified_at,
            "archived": self.archived,
            "archived_at": self.archived_at,
            "archived_by": self.archived_by,
            "action_history": list(self.action_history),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobState":
        created_at = str(payload.get("created_at") or utc_now_iso())
        last_modified_at = str(payload.get("last_modified_at") or created_at)
        status = dict(payload.get("status") or {})
        status.setdefault("current_status", "ready")
        status.setdefault("last_action", "")
        status.setdefault("last_updated", last_modified_at)
        status.setdefault("messages", [])
        status.setdefault("actions", {})
        status.setdefault("steps", {})
        return cls(
            job_id=str(payload.get("job_id") or ""),
            title=str(payload.get("title") or ""),
            region=str(payload.get("region") or ""),
            created_at=created_at,
            job_dir=str(payload.get("job_dir") or ""),
            inputs={str(key): str(value) for key, value in (payload.get("inputs") or {}).items()},
            artifacts=[JobArtifact.from_dict(item) for item in payload.get("artifacts") or []],
            status=status,
            operator_name=str(payload.get("operator_name") or ""),
            last_modified_by=str(payload.get("last_modified_by") or ""),
            last_modified_at=last_modified_at,
            archived=bool(payload.get("archived", False)),
            archived_at=str(payload.get("archived_at") or ""),
            archived_by=str(payload.get("archived_by") or ""),
            action_history=list(payload.get("action_history") or []),
        )


def load_job_state(path: str | Path) -> JobState:
    """Load a job state JSON file."""

    state_path = Path(path)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return JobState.from_dict(payload)


def save_job_state(job: JobState) -> Path:
    """Persist a job state JSON file."""

    ensure_parent(job.state_path)
    job.state_path.write_text(json.dumps(job.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8")
    return job.state_path
