from pathlib import Path

from src.models import AppConfig
from ui.job_manager import (
    archive_job,
    build_artifact_records,
    create_job,
    current_step_snapshot,
    delete_job,
    load_job,
    record_artifact_version,
    restore_job,
    save_existing_input,
    set_job_step_status,
    update_operator,
    workspace_root,
)


def test_create_job_persists_workspace_structure_and_state(tmp_path) -> None:
    config = AppConfig(data={"ui": {"workspace_root": str(tmp_path / "jobs")}, "app": {"default_region": "Nairobi"}})

    job = create_job(config, "Proposed Health Centre", "Nairobi", "Ron")

    job_dir = Path(job.job_dir)
    assert workspace_root(config) == tmp_path / "jobs"
    assert (job_dir / "inputs").exists()
    assert (job_dir / "intermediate").exists()
    assert (job_dir / "outputs").exists()
    assert (job_dir / "logs").exists()
    assert (job_dir / "state.json").exists()
    assert job.operator_name == "Ron"
    assert job.last_modified_by == "Ron"


def test_artifact_versioning_keeps_history_and_latest_pointer(tmp_path) -> None:
    config = AppConfig(data={"ui": {"workspace_root": str(tmp_path / "jobs")}, "app": {"default_region": "Nairobi"}})
    job = create_job(config, "Drainage Works", "Nyanza", "Estimator A")

    first = Path(job.job_dir) / "outputs" / "analysis_r01.xlsx"
    second = Path(job.job_dir) / "outputs" / "analysis_r02.xlsx"
    first.write_bytes(b"v1")
    second.write_bytes(b"v2")

    record_artifact_version(job, "tender_analysis_workbook", "Tender Analysis Workbook", first, "analyze_tender", "completed", "Estimator A")
    record_artifact_version(job, "tender_analysis_workbook", "Tender Analysis Workbook", second, "analyze_tender", "completed", "Estimator B")

    loaded = load_job(config, job.job_id)
    records = build_artifact_records(loaded)

    assert records[0]["latest_path"] == str(second)
    assert records[0]["created_by"] == "Estimator B"
    assert len(records[0]["versions"]) == 2
    assert records[0]["versions"][0]["path"] == str(second)


def test_step_status_persistence_tracks_running_completed_and_failed(tmp_path) -> None:
    config = AppConfig(data={"ui": {"workspace_root": str(tmp_path / "jobs")}, "app": {"default_region": "Nairobi"}})
    job = create_job(config, "Gap Review", "Nairobi", "QS One")

    set_job_step_status(job, "analyze_tender", "running", "Starting analysis.", "QS One")
    set_job_step_status(job, "analyze_tender", "completed", "Analysis complete.", "QS One")
    set_job_step_status(job, "draft_boq", "failed", "Drafting failed.", "QS Two")

    loaded = load_job(config, job.job_id)
    steps = current_step_snapshot(loaded)

    assert steps["analyze_tender"]["status"] == "completed"
    assert steps["analyze_tender"]["completed_at"]
    assert steps["draft_boq"]["status"] == "failed"
    assert steps["draft_boq"]["last_error"] == "Drafting failed."


def test_archive_restore_and_delete_job_behaviour(tmp_path) -> None:
    config = AppConfig(data={"ui": {"workspace_root": str(tmp_path / "jobs")}, "app": {"default_region": "Nairobi"}})
    job = create_job(config, "Archive Test", "Nairobi", "Admin")

    archive_job(job, "Admin")
    archived = load_job(config, job.job_id)
    assert archived.archived is True
    assert archived.archived_by == "Admin"

    restore_job(archived, "Admin")
    restored = load_job(config, job.job_id)
    assert restored.archived is False

    delete_job(config, restored, "Admin")
    assert not Path(restored.job_dir).exists()


def test_operator_attribution_and_input_persistence_round_trip(tmp_path) -> None:
    config = AppConfig(data={"ui": {"workspace_root": str(tmp_path / "jobs")}, "app": {"default_region": "Nairobi"}})
    source = tmp_path / "demo_tender.txt"
    source.write_text("Tender text", encoding="utf-8")

    job = create_job(config, "Operator Test", "Nyanza", "Operator A")
    save_existing_input(job, "tender", str(source), "Operator A")
    update_operator(job, "Operator B")

    loaded = load_job(config, job.job_id)

    assert loaded.inputs["tender"].endswith("tender__demo_tender.txt")
    assert loaded.operator_name == "Operator B"
    assert loaded.last_modified_by == "Operator B"
    assert any(entry["action"] == "operator_update" for entry in loaded.action_history)
