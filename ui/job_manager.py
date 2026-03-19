"""Workspace job management and action orchestration for the Streamlit UI."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any, Callable
from uuid import uuid4

from src.utils import ensure_parent, slugify

from .helpers import read_binary
from .state_store import (
    JobArtifact,
    JobArtifactVersion,
    JobState,
    load_job_state,
    save_job_state,
    utc_now_iso,
)


STEP_KEYS = ("analyze_tender", "draft_boq", "gap_check", "tender_price", "boq_price")
STEP_LABELS = {
    "analyze_tender": "Analyze Tender",
    "draft_boq": "Generate Draft BOQ",
    "gap_check": "Run Gap Check",
    "tender_price": "Run Tender -> Pricing",
    "boq_price": "Price BOQ Only",
}
ARTIFACT_STEP_MAP = {
    "tender_analysis_workbook": "analyze_tender",
    "tender_analysis_json": "analyze_tender",
    "draft_boq_workbook": "draft_boq",
    "draft_boq_json": "draft_boq",
    "gap_check_workbook": "gap_check",
    "gap_check_json": "gap_check",
    "tender_price_workbook": "tender_price",
    "tender_price_json": "tender_price",
    "tender_price_audit_json": "tender_price",
    "pricing_handoff_workbook": "tender_price",
    "boq_price_workbook": "boq_price",
    "boq_price_unmatched_csv": "boq_price",
    "boq_price_audit_json": "boq_price",
}
STEP_STATUS_DEFAULT = {
    "status": "not_started",
    "started_at": "",
    "completed_at": "",
    "failed_at": "",
    "last_outcome": "",
    "last_error": "",
    "last_run_by": "",
    "latest_artifact_types": [],
}


def _default_steps() -> dict[str, dict[str, Any]]:
    return {step: dict(STEP_STATUS_DEFAULT) for step in STEP_KEYS}


def _operator_name(job: JobState, session_state: Any | None = None) -> str:
    session_value = ""
    if session_state is not None:
        session_value = str(session_state.get("operator_name", "")).strip()
    return session_value or job.operator_name or "Office User"


def _touch_modified(job: JobState, operator_name: str) -> None:
    timestamp = utc_now_iso()
    job.last_modified_by = operator_name
    job.last_modified_at = timestamp
    if not job.operator_name:
        job.operator_name = operator_name
    job.status["last_updated"] = timestamp


def _append_action_history(job: JobState, action: str, status: str, message: str, operator_name: str, details: dict[str, Any] | None = None) -> None:
    job.action_history.append(
        {
            "timestamp": utc_now_iso(),
            "action": action,
            "status": status,
            "message": message,
            "operator_name": operator_name,
            "details": details or {},
        }
    )
    job.action_history = job.action_history[-50:]


def set_active_job_id(session_state: Any, job_id: str) -> None:
    """Store the active job id in session state."""

    session_state["active_job_id"] = job_id


def set_session_operator_name(session_state: Any, operator_name: str) -> None:
    """Store the current UI operator display name in session state."""

    session_state["operator_name"] = operator_name.strip()


def get_active_job(config: Any, session_state: Any) -> JobState | None:
    """Load the active job from session state when available."""

    job_id = str(session_state.get("active_job_id", "")).strip()
    if not job_id:
        return None
    try:
        return load_job(config, job_id)
    except Exception:
        return None


def workspace_root(config: Any) -> Path:
    """Return the root folder for persisted workspace jobs."""

    root = Path(str(config.get("ui.workspace_root", "workspace/jobs")))
    root.mkdir(parents=True, exist_ok=True)
    return root


def list_jobs(config: Any, include_archived: bool = False) -> list[JobState]:
    """List all persisted jobs newest first."""

    jobs: list[JobState] = []
    for state_path in workspace_root(config).glob("*/state.json"):
        try:
            job = load_job_state(state_path)
        except Exception:
            continue
        if not include_archived and job.archived:
            continue
        jobs.append(job)
    return sorted(jobs, key=lambda item: item.last_modified_at or item.created_at, reverse=True)


def create_job(config: Any, title: str, region: str, operator_name: str = "") -> JobState:
    """Create a new persisted job workspace."""

    safe_title = slugify(title or "job")
    job_id = f"{safe_title}_{uuid4().hex[:8]}"
    job_dir = workspace_root(config) / job_id
    for folder_name in ("inputs", "intermediate", "outputs", "logs"):
        (job_dir / folder_name).mkdir(parents=True, exist_ok=True)

    created_at = utc_now_iso()
    operator = operator_name.strip() or "Office User"
    job = JobState(
        job_id=job_id,
        title=title.strip() or "Untitled Job",
        region=region.strip() or str(config.default_region),
        created_at=created_at,
        job_dir=str(job_dir),
        status={
            "current_status": "ready",
            "last_action": "",
            "last_updated": created_at,
            "messages": [],
            "actions": {},
            "steps": _default_steps(),
        },
        operator_name=operator,
        last_modified_by=operator,
        last_modified_at=created_at,
    )
    _append_action_history(job, "job_created", "completed", f"Job created: {job.title}", operator, {})
    save_job_state(job)
    append_job_log(job, f"job_created | completed | operator={operator} | title={job.title}")
    return job


def load_job(config: Any, job_id: str) -> JobState:
    """Load a job by id."""

    state_path = workspace_root(config) / job_id / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"Job not found: {job_id}")
    return load_job_state(state_path)


def save_job(job: JobState) -> JobState:
    """Persist and return the updated job."""

    save_job_state(job)
    return job


def append_job_log(job: JobState, message: str) -> Path:
    """Append a lightweight per-job log line."""

    log_path = Path(job.job_dir) / "logs" / "workspace.log"
    ensure_parent(log_path)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now_iso()} | {message}\n")
    return log_path


def update_operator(job: JobState, operator_name: str) -> JobState:
    """Persist the current operator display name for the job."""

    operator = operator_name.strip() or "Office User"
    job.operator_name = operator
    _touch_modified(job, operator)
    _append_action_history(job, "operator_update", "completed", f"Operator set to {operator}.", operator, {})
    append_job_log(job, f"operator_update | completed | operator={operator}")
    return save_job(job)


def update_job_metadata(job: JobState, title: str | None = None, region: str | None = None, operator_name: str = "") -> JobState:
    """Update persisted job metadata."""

    operator = operator_name.strip() or _operator_name(job)
    if title is not None and title.strip():
        job.title = title.strip()
    if region is not None and region.strip():
        job.region = region.strip()
    _touch_modified(job, operator)
    _append_action_history(job, "job_updated", "completed", "Job details updated.", operator, {"title": job.title, "region": job.region})
    append_job_log(job, f"job_updated | completed | operator={operator} | title={job.title} | region={job.region}")
    return save_job(job)


def archive_job(job: JobState, operator_name: str) -> JobState:
    """Archive a job without deleting its files."""

    operator = operator_name.strip() or _operator_name(job)
    job.archived = True
    job.archived_at = utc_now_iso()
    job.archived_by = operator
    _touch_modified(job, operator)
    _append_action_history(job, "job_archived", "completed", "Job archived.", operator, {})
    append_job_log(job, f"job_archived | completed | operator={operator}")
    return save_job(job)


def restore_job(job: JobState, operator_name: str) -> JobState:
    """Restore an archived job."""

    operator = operator_name.strip() or _operator_name(job)
    job.archived = False
    job.archived_at = ""
    job.archived_by = ""
    _touch_modified(job, operator)
    _append_action_history(job, "job_restored", "completed", "Job restored.", operator, {})
    append_job_log(job, f"job_restored | completed | operator={operator}")
    return save_job(job)


def delete_job(config: Any, job: JobState, operator_name: str) -> None:
    """Delete a job directory permanently."""

    operator = operator_name.strip() or _operator_name(job)
    append_job_log(job, f"job_deleted | completed | operator={operator}")
    shutil.rmtree(Path(job.job_dir), ignore_errors=False)


def get_input_path(job: JobState, key: str) -> Path | None:
    """Return a stored input path if present and still on disk."""

    raw = job.inputs.get(key, "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.exists() else None


def save_uploaded_input(job: JobState, key: str, uploaded_file: Any, operator_name: str = "") -> Path:
    """Persist an uploaded input file into the job workspace."""

    operator = operator_name.strip() or _operator_name(job)
    suffix = Path(uploaded_file.name).suffix
    destination = Path(job.job_dir) / "inputs" / f"{key}__{slugify(Path(uploaded_file.name).stem)}{suffix}"
    ensure_parent(destination)
    destination.write_bytes(uploaded_file.getbuffer())
    job.inputs[key] = str(destination)
    _touch_modified(job, operator)
    _append_action_history(job, "file_uploaded", "completed", f"Saved uploaded {key}.", operator, {"input_key": key, "path": str(destination)})
    append_job_log(job, f"file_uploaded | completed | operator={operator} | input={key} | path={destination}")
    save_job(job)
    return destination


def save_existing_input(job: JobState, key: str, source_path: str, operator_name: str = "") -> Path:
    """Copy an existing file path into the job workspace inputs folder."""

    operator = operator_name.strip() or _operator_name(job)
    source = Path(source_path.strip())
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")
    destination = Path(job.job_dir) / "inputs" / f"{key}__{source.name}"
    ensure_parent(destination)
    shutil.copy2(source, destination)
    job.inputs[key] = str(destination)
    _touch_modified(job, operator)
    _append_action_history(job, "file_copied", "completed", f"Copied existing {key}.", operator, {"input_key": key, "path": str(destination)})
    append_job_log(job, f"file_copied | completed | operator={operator} | input={key} | path={destination}")
    save_job(job)
    return destination


def _ensure_step(job: JobState, step: str) -> dict[str, Any]:
    steps = job.status.setdefault("steps", _default_steps())
    if step not in steps:
        steps[step] = dict(STEP_STATUS_DEFAULT)
    return steps[step]


def set_job_step_status(job: JobState, step: str, status: str, message: str, operator_name: str) -> JobState:
    """Update persisted step metadata."""

    operator = operator_name.strip() or _operator_name(job)
    step_state = _ensure_step(job, step)
    timestamp = utc_now_iso()
    step_state["status"] = status
    step_state["last_outcome"] = message
    step_state["last_run_by"] = operator
    if status == "running":
        step_state["started_at"] = timestamp
        step_state["last_error"] = ""
    elif status == "completed":
        step_state["completed_at"] = timestamp
        step_state["failed_at"] = ""
        step_state["last_error"] = ""
    elif status == "failed":
        step_state["failed_at"] = timestamp
        step_state["last_error"] = message
    job.status["current_status"] = status
    job.status["last_action"] = step
    messages = job.status.setdefault("messages", [])
    messages.append(f"{timestamp} | {STEP_LABELS.get(step, step)} | {status} | {message}")
    job.status["messages"] = messages[-15:]
    actions = job.status.setdefault("actions", {})
    actions[step] = {"status": status, "message": message, "updated_at": timestamp}
    _touch_modified(job, operator)
    _append_action_history(job, step, status, message, operator, {})
    append_job_log(job, f"{step} | {status} | operator={operator} | {message}")
    return save_job(job)


def _artifact_output_path(job: JobState, artifact_type: str, extension: str, folder: str = "outputs") -> Path:
    base = Path(job.job_dir) / folder
    stem = f"{slugify(job.title)}_{artifact_type}"
    existing = list(base.glob(f"{stem}_r*{extension}"))
    revision = len(existing) + 1
    timestamp = utc_now_iso().replace(":", "").replace("-", "")
    return base / f"{stem}_r{revision:02d}_{timestamp}{extension}"


def record_artifact_version(
    job: JobState,
    artifact_type: str,
    label: str,
    path: str | Path,
    action: str,
    status: str,
    operator_name: str,
) -> JobArtifact:
    """Append a new artifact version and update latest pointers."""

    operator = operator_name.strip() or _operator_name(job)
    artifact_path = str(Path(path))
    artifact = next((item for item in job.artifacts if item.artifact_type == artifact_type), None)
    version_id = f"v{(len(artifact.versions) + 1) if artifact else 1}"
    version = JobArtifactVersion(
        version_id=version_id,
        path=artifact_path,
        status=status,
        created_at=utc_now_iso(),
        created_by=operator,
    )
    if artifact is None:
        artifact = JobArtifact(
            artifact_id=f"{artifact_type}_{uuid4().hex[:8]}",
            artifact_type=artifact_type,
            label=label,
            action=action,
            latest_path=artifact_path,
            latest_status=status,
            latest_created_at=version.created_at,
            latest_created_by=operator,
            versions=[version],
        )
        job.artifacts.append(artifact)
    else:
        artifact.label = label
        artifact.action = action
        artifact.latest_path = artifact_path
        artifact.latest_status = status
        artifact.latest_created_at = version.created_at
        artifact.latest_created_by = operator
        artifact.versions.append(version)
    _touch_modified(job, operator)
    _append_action_history(job, "artifact_written", status, f"{label} saved as {version_id}.", operator, {"artifact_type": artifact_type, "path": artifact_path})
    append_job_log(job, f"artifact_written | {status} | operator={operator} | type={artifact_type} | version={version_id} | path={artifact_path}")
    save_job(job)
    return artifact


def build_artifact_records(job: JobState) -> list[dict[str, Any]]:
    """Return artifact metadata for rendering."""

    records: list[dict[str, Any]] = []
    for artifact in sorted(job.artifacts, key=lambda item: item.latest_created_at, reverse=True):
        records.append(
            {
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "label": artifact.label,
                "status": artifact.latest_status,
                "created_at": artifact.latest_created_at,
                "created_by": artifact.latest_created_by,
                "latest_path": artifact.latest_path,
                "action": artifact.action,
                "versions": [
                    {
                        "version_id": version.version_id,
                        "path": version.path,
                        "status": version.status,
                        "created_at": version.created_at,
                        "created_by": version.created_by,
                    }
                    for version in reversed(artifact.versions)
                ],
            }
        )
    return records


def require_job_input(job: JobState, key: str, label: str) -> Path:
    """Require a persisted job input."""

    path = get_input_path(job, key)
    if path is None:
        raise ValueError(f"{label} is not set for this job. Open Workspace / Jobs and add it first.")
    return path


def resolve_job_database_path(runtime, job: JobState) -> Path:
    """Resolve the saved job database path or fall back to the runtime default."""

    fallback = Path(str(getattr(runtime, "default_database_path", "")).strip())
    if getattr(runtime, "app_mode", "production") == "production":
        if fallback.exists():
            return fallback
        raise ValueError("Production database snapshot is not available. Ask the owner/admin to publish a release.")

    saved_path = get_input_path(job, "database")
    if saved_path is not None:
        return saved_path
    if fallback.exists():
        return fallback
    raise ValueError("Database workbook is not set for this job and no default app database is available.")


def current_step_snapshot(job: JobState) -> dict[str, dict[str, Any]]:
    """Return the persisted step status mapping."""

    steps = job.status.get("steps") or _default_steps()
    for step in STEP_KEYS:
        steps.setdefault(step, dict(STEP_STATUS_DEFAULT))
    return steps


def suggest_next_step(job: JobState) -> str:
    """Suggest the next logical step for the workspace job."""

    steps = current_step_snapshot(job)
    if get_input_path(job, "tender") is None:
        return "Add a tender input to begin."
    if steps["analyze_tender"]["status"] != "completed":
        return "Analyze Tender"
    if steps["draft_boq"]["status"] != "completed":
        return "Generate Draft BOQ"
    if steps["gap_check"]["status"] != "completed":
        return "Run Gap Check"
    if get_input_path(job, "database") is None:
        return "Add a database workbook before pricing."
    if get_input_path(job, "boq") is not None and steps["boq_price"]["status"] != "completed":
        return "Price BOQ Only"
    if steps["tender_price"]["status"] != "completed":
        return "Run Tender -> Pricing"
    return "Review latest artifacts and rerun any step if needed."


def latest_successful_artifacts(job: JobState) -> dict[str, str]:
    """Return latest completed artifact paths by type."""

    latest: dict[str, str] = {}
    for artifact in job.artifacts:
        if artifact.latest_status == "completed" and Path(artifact.latest_path).exists():
            latest[artifact.artifact_type] = artifact.latest_path
    return latest


def _run_step(job: JobState, step: str, operator_name: str, runner: Callable[[], list[tuple[str, str, str | Path, str]]]) -> JobState:
    set_job_step_status(job, step, "running", "Step started.", operator_name)
    try:
        artifact_payloads = runner()
    except Exception as exc:
        set_job_step_status(job, step, "failed", str(exc).strip() or "Step failed.", operator_name)
        raise

    written_types: list[str] = []
    for artifact_type, label, path, status in artifact_payloads:
        record_artifact_version(job, artifact_type, label, path, step, status, operator_name)
        written_types.append(artifact_type)

    step_state = _ensure_step(job, step)
    step_state["latest_artifact_types"] = written_types
    set_job_step_status(job, step, "completed", "Step completed successfully.", operator_name)
    return save_job(job)


def run_analyze_tender(runtime, job: JobState, title_override: str | None = None, operator_name: str = "") -> JobState:
    """Run tender analysis within a job workspace."""

    operator = operator_name.strip() or _operator_name(job)
    tender_path = require_job_input(job, "tender", "Tender input")
    output_path = _artifact_output_path(job, "tender_analysis_workbook", ".xlsx")
    json_path = _artifact_output_path(job, "tender_analysis_json", ".json")

    def _runner():
        result = runtime.tender_workflow.analyze(
            input_path=str(tender_path),
            output_path=str(output_path),
            json_path=str(json_path),
            title_override=title_override or job.title,
        )
        payloads = [("tender_analysis_workbook", "Tender Analysis Workbook", result.output_workbook, "completed")]
        if result.output_json:
            payloads.append(("tender_analysis_json", "Tender Analysis JSON", result.output_json, "completed"))
        return payloads

    return _run_step(job, "analyze_tender", operator, _runner)


def run_draft_boq(runtime, job: JobState, title_override: str | None = None, operator_name: str = "") -> JobState:
    """Run draft BOQ generation within a job workspace."""

    operator = operator_name.strip() or _operator_name(job)
    tender_path = require_job_input(job, "tender", "Tender input")
    output_path = _artifact_output_path(job, "draft_boq_workbook", ".xlsx")
    json_path = _artifact_output_path(job, "draft_boq_json", ".json")

    def _runner():
        result = runtime.tender_workflow.draft_boq(
            input_path=str(tender_path),
            output_path=str(output_path),
            json_path=str(json_path),
            title_override=title_override or job.title,
        )
        payloads = [("draft_boq_workbook", "Draft BOQ Workbook", result.output_workbook, "completed")]
        if result.output_json:
            payloads.append(("draft_boq_json", "Draft BOQ JSON", result.output_json, "completed"))
        return payloads

    return _run_step(job, "draft_boq", operator, _runner)


def run_gap_check(runtime, job: JobState, title_override: str | None = None, operator_name: str = "") -> JobState:
    """Run gap check within a job workspace."""

    operator = operator_name.strip() or _operator_name(job)
    tender_path = require_job_input(job, "tender", "Tender input")
    boq_path = get_input_path(job, "boq")
    output_path = _artifact_output_path(job, "gap_check_workbook", ".xlsx")
    json_path = _artifact_output_path(job, "gap_check_json", ".json")

    def _runner():
        result = runtime.tender_workflow.gap_check(
            input_path=str(tender_path),
            output_path=str(output_path),
            boq_path=str(boq_path) if boq_path else None,
            json_path=str(json_path),
            title_override=title_override or job.title,
        )
        payloads = [("gap_check_workbook", "Gap Check Workbook", result.output_workbook, "completed")]
        if result.output_json:
            payloads.append(("gap_check_json", "Gap Check JSON", result.output_json, "completed"))
        return payloads

    return _run_step(job, "gap_check", operator, _runner)


def run_tender_pricing(runtime, job: JobState, threshold: float, apply_rates: bool, title_override: str | None = None, operator_name: str = "", matching_mode: str = "rule") -> JobState:
    """Run the integrated tender-to-pricing workflow within a job workspace."""

    operator = operator_name.strip() or _operator_name(job)
    tender_path = require_job_input(job, "tender", "Tender input")
    db_path = resolve_job_database_path(runtime, job)
    boq_path = get_input_path(job, "boq")
    output_path = _artifact_output_path(job, "tender_price_workbook", ".xlsx")
    json_path = _artifact_output_path(job, "tender_price_json", ".json")

    def _runner():
        artifacts = runtime.tender_to_price_runner.run(
            input_path=str(tender_path),
            db_path=str(db_path),
            output_path=str(output_path),
            boq_path=str(boq_path) if boq_path else None,
            region=job.region,
            threshold=threshold,
            apply_rates=apply_rates,
            title_override=title_override or job.title,
            json_path=str(json_path),
            matching_mode=matching_mode,
        )
        payloads = [("tender_price_workbook", "Tender Pricing Workbook", artifacts.output_workbook, "completed")]
        if artifacts.handoff_workbook:
            payloads.append(("pricing_handoff_workbook", "Pricing Handoff Workbook", artifacts.handoff_workbook, "completed"))
        if artifacts.output_json:
            payloads.append(("tender_price_json", "Tender Pricing JSON", artifacts.output_json, "completed"))
        if artifacts.pricing_artifacts and artifacts.pricing_artifacts.audit_json:
            payloads.append(("tender_price_audit_json", "Tender Pricing Audit JSON", artifacts.pricing_artifacts.audit_json, "completed"))
        return payloads

    return _run_step(job, "tender_price", operator, _runner)


def run_price_boq(runtime, job: JobState, threshold: float, apply_rates: bool, operator_name: str = "", matching_mode: str = "rule") -> JobState:
    """Run BOQ pricing within a job workspace."""

    operator = operator_name.strip() or _operator_name(job)
    boq_path = require_job_input(job, "boq", "BOQ workbook")
    db_path = resolve_job_database_path(runtime, job)
    output_path = _artifact_output_path(job, "boq_price_workbook", ".xlsx")

    def _runner():
        artifacts = runtime.pricing_engine.price_workbook(
            db_path=str(db_path),
            boq_path=str(boq_path),
            output_path=str(output_path),
            region=job.region,
            threshold=threshold,
            apply_rates=apply_rates,
            matching_mode=matching_mode,
        )
        payloads = [("boq_price_workbook", "Priced BOQ Workbook", artifacts.output_workbook, "completed")]
        if artifacts.unmatched_csv:
            payloads.append(("boq_price_unmatched_csv", "Unmatched CSV", artifacts.unmatched_csv, "completed"))
        if artifacts.audit_json:
            payloads.append(("boq_price_audit_json", "Pricing Audit JSON", artifacts.audit_json, "completed"))
        return payloads

    return _run_step(job, "boq_price", operator, _runner)
