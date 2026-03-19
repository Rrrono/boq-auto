"""Workspace and job management page for the Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .helpers import read_binary, safe_error_message
from .job_manager import (
    STEP_LABELS,
    archive_job,
    build_artifact_records,
    create_job,
    current_step_snapshot,
    delete_job,
    get_active_job,
    get_input_path,
    latest_successful_artifacts,
    list_jobs,
    restore_job,
    run_analyze_tender,
    run_draft_boq,
    run_gap_check,
    run_price_boq,
    run_tender_pricing,
    save_existing_input,
    save_uploaded_input,
    set_active_job_id,
    set_session_operator_name,
    suggest_next_step,
    update_job_metadata,
    update_operator,
    workspace_root,
)


def _job_label(job) -> str:
    archived = " (Archived)" if job.archived else ""
    return f"{job.title} [{job.job_id}]{archived}"


def _current_operator(job) -> str:
    return str(st.session_state.get("operator_name", "")).strip() or job.operator_name or "Office User"


def _run_action(runtime, job, action: str, title_override: str, threshold: float, apply_rates: bool, operator_name: str):
    if action == "analyze_tender":
        return run_analyze_tender(runtime, job, title_override or None, operator_name)
    if action == "draft_boq":
        return run_draft_boq(runtime, job, title_override or None, operator_name)
    if action == "gap_check":
        return run_gap_check(runtime, job, title_override or None, operator_name)
    if action == "tender_price":
        return run_tender_pricing(runtime, job, threshold, apply_rates, title_override or None, operator_name)
    if action == "boq_price":
        return run_price_boq(runtime, job, threshold, apply_rates, operator_name)
    raise ValueError(f"Unsupported workspace action: {action}")


def _render_input_slot(job, key: str, label: str, file_types: list[str], operator_name: str) -> None:
    current_path = get_input_path(job, key)
    st.markdown(f"**{label}**")
    st.caption(str(current_path) if current_path else "Not set yet.")
    uploaded = st.file_uploader(f"Upload {label}", type=file_types, key=f"workspace_{job.job_id}_{key}_upload")
    existing_path = st.text_input(f"Or copy existing {label} path", value="", key=f"workspace_{job.job_id}_{key}_path")
    action_cols = st.columns(2)
    if action_cols[0].button(f"Save uploaded {label}", key=f"workspace_{job.job_id}_{key}_save_upload", disabled=uploaded is None):
        save_uploaded_input(job, key, uploaded, operator_name)
        st.success(f"Saved {label} into this job workspace.")
        st.rerun()
    if action_cols[1].button(f"Copy existing {label}", key=f"workspace_{job.job_id}_{key}_save_path", disabled=not existing_path.strip()):
        save_existing_input(job, key, existing_path, operator_name)
        st.success(f"Copied {label} into this job workspace.")
        st.rerun()


def _render_step_status(job) -> None:
    st.subheader("Step Status")
    steps = current_step_snapshot(job)
    for step_key, label in STEP_LABELS.items():
        step = steps[step_key]
        with st.container(border=True):
            st.write(
                {
                    "step": label,
                    "status": step["status"],
                    "last_outcome": step["last_outcome"],
                    "last_run_by": step["last_run_by"],
                    "started_at": step["started_at"],
                    "completed_at": step["completed_at"],
                    "failed_at": step["failed_at"],
                }
            )


def _render_artifacts(runtime, job, title_override: str, threshold: float, apply_rates: bool, operator_name: str) -> None:
    st.subheader("Artifacts")
    records = build_artifact_records(job)
    if not records:
        st.info("No artifacts yet. Run one of the workspace actions to generate review or pricing outputs.")
        return

    for record in records:
        latest_path = Path(record["latest_path"])
        with st.container(border=True):
            header_cols = st.columns([2, 1, 2, 2, 1, 1])
            header_cols[0].write(record["label"])
            header_cols[1].write(record["status"])
            header_cols[2].write(record["created_at"])
            header_cols[3].write(record["created_by"] or "Office User")
            header_cols[4].caption(record["artifact_type"])
            if latest_path.exists():
                header_cols[5].download_button(
                    "Download Latest",
                    data=read_binary(latest_path),
                    file_name=latest_path.name,
                    mime="application/octet-stream",
                    key=f"artifact_download_{record['artifact_id']}",
                )

            st.caption(f"Latest file: {latest_path}")
            control_cols = st.columns([1, 4])
            if control_cols[0].button("Rerun", key=f"artifact_rerun_{record['artifact_id']}"):
                try:
                    updated_job = _run_action(runtime, job, record["action"], title_override, threshold, apply_rates, operator_name)
                    set_active_job_id(st.session_state, updated_job.job_id)
                    st.success(f"{STEP_LABELS.get(record['action'], record['action'])} rerun completed with a new artifact version.")
                    st.rerun()
                except Exception as exc:
                    st.error(safe_error_message(exc))
            with st.expander("Version History"):
                for version in record["versions"]:
                    version_path = Path(version["path"])
                    version_cols = st.columns([1, 2, 2, 3, 1])
                    version_cols[0].write(version["version_id"])
                    version_cols[1].write(version["status"])
                    version_cols[2].write(version["created_by"] or "Office User")
                    version_cols[3].caption(str(version_path))
                    if version_path.exists():
                        version_cols[4].download_button(
                            "Download",
                            data=read_binary(version_path),
                            file_name=version_path.name,
                            mime="application/octet-stream",
                            key=f"artifact_version_download_{record['artifact_id']}_{version['version_id']}",
                        )


def render(runtime) -> None:
    """Render the job workspace page."""

    st.header("Workspace / Jobs")
    st.write("Create, reopen, run, rerun, and trace one persistent job without re-uploading files between steps.")
    if runtime.app_mode == "production":
        st.caption(f"Production pricing actions automatically use the current released database snapshot: {runtime.default_database_path}")
    else:
        st.caption(f"Admin mode defaults to the master/training database: {runtime.default_database_path}")

    session_operator = st.text_input("Operator / Display Name", value=str(st.session_state.get("operator_name", "")), key="workspace_operator_name")
    if st.button("Set Operator Name", key="workspace_set_operator"):
        set_session_operator_name(st.session_state, session_operator)
        st.success("Operator name saved for this session.")
        st.rerun()

    show_archived = st.checkbox("Show archived jobs", value=False, key="workspace_show_archived")
    jobs = list_jobs(runtime.config, include_archived=show_archived)
    job_map = {job.job_id: job for job in jobs}
    active_job = get_active_job(runtime.config, st.session_state)

    create_col, open_col = st.columns(2)
    with create_col:
        st.subheader("Create Job")
        job_title = st.text_input("Job title", value="")
        job_region = st.text_input("Region", value=runtime.config.default_region)
        if st.button("Create Workspace Job", type="primary", key="workspace_create_job"):
            operator = session_operator.strip() or "Office User"
            set_session_operator_name(st.session_state, operator)
            job = create_job(runtime.config, job_title or "New Tender Job", job_region, operator)
            set_active_job_id(st.session_state, job.job_id)
            st.success(f"Created job {job.title}.")
            st.rerun()

    with open_col:
        st.subheader("Reopen Job")
        selected_job_id = st.selectbox(
            "Existing jobs",
            options=[""] + [job.job_id for job in jobs],
            format_func=lambda value: "Select a saved job" if not value else _job_label(job_map[value]),
        )
        if st.button("Open Selected Job", key="workspace_open_job", disabled=not selected_job_id):
            set_active_job_id(st.session_state, selected_job_id)
            st.success("Workspace job opened.")
            st.rerun()

    if active_job is None:
        st.info(f"No active job selected. Jobs are stored under {workspace_root(runtime.config)}.")
        return

    current_operator = _current_operator(active_job)
    if current_operator != active_job.operator_name:
        update_operator(active_job, current_operator)
        active_job = get_active_job(runtime.config, st.session_state) or active_job

    st.divider()
    st.subheader("Active Job")
    st.write(
        {
            "job_id": active_job.job_id,
            "title": active_job.title,
            "region": active_job.region,
            "created_at": active_job.created_at,
            "operator_name": active_job.operator_name,
            "last_modified_by": active_job.last_modified_by,
            "last_modified_at": active_job.last_modified_at,
            "archived": active_job.archived,
            "job_dir": active_job.job_dir,
            "resolved_database": active_job.inputs.get("database") or runtime.default_database_path,
        }
    )
    st.info(f"Suggested next step: {suggest_next_step(active_job)}")
    successful = latest_successful_artifacts(active_job)
    if successful:
        st.caption(f"Latest successful artifacts detected: {', '.join(sorted(successful.keys()))}")

    meta_col, status_col = st.columns([2, 1])
    with meta_col:
        new_title = st.text_input("Edit job title", value=active_job.title, key=f"workspace_title_{active_job.job_id}")
        new_region = st.text_input("Edit job region", value=active_job.region, key=f"workspace_region_{active_job.job_id}")
        if st.button("Update Job Details", key=f"workspace_update_{active_job.job_id}"):
            update_job_metadata(active_job, new_title, new_region, current_operator)
            st.success("Job details updated.")
            st.rerun()
    with status_col:
        st.caption("Recent status")
        st.json(active_job.status.get("actions", {}))

    manage_col, delete_col = st.columns(2)
    with manage_col:
        if active_job.archived:
            if st.button("Restore Job", key=f"workspace_restore_{active_job.job_id}"):
                restore_job(active_job, current_operator)
                st.success("Job restored.")
                st.rerun()
        else:
            if st.button("Archive Job", key=f"workspace_archive_{active_job.job_id}"):
                archive_job(active_job, current_operator)
                st.success("Job archived. Hidden from the default list but recoverable.")
                st.rerun()
    with delete_col:
        confirm_delete = st.checkbox("I understand delete is permanent", key=f"workspace_delete_confirm_{active_job.job_id}")
        if st.button("Delete Job Permanently", key=f"workspace_delete_{active_job.job_id}", disabled=not confirm_delete):
            delete_job(runtime.config, active_job, current_operator)
            st.session_state.pop("active_job_id", None)
            st.success("Job deleted permanently.")
            st.rerun()

    st.subheader("Saved Inputs")
    _render_input_slot(active_job, "tender", "Tender input", ["pdf", "txt", "md", "csv", "xlsx", "xlsm"], current_operator)
    _render_input_slot(active_job, "boq", "BOQ workbook", ["xlsx", "xlsm"], current_operator)
    if runtime.app_mode == "admin":
        _render_input_slot(active_job, "database", "Database workbook", ["xlsx", "xlsm"], current_operator)
    else:
        st.markdown("**Database workbook**")
        st.caption(f"Production app uses the current released snapshot automatically: {runtime.default_database_path}")

    st.subheader("Workspace Actions")
    title_override = st.text_input("Tender title override", value=active_job.title, key=f"workspace_title_override_{active_job.job_id}")
    threshold = st.number_input(
        "Matching threshold",
        min_value=0.0,
        max_value=100.0,
        value=float(runtime.config.get("matching.threshold", 78)),
        key=f"workspace_threshold_{active_job.job_id}",
    )
    apply_rates = st.checkbox(
        "Apply rates into priced workbook",
        value=bool(runtime.config.get("processing.apply_rates", False)),
        key=f"workspace_apply_{active_job.job_id}",
    )

    tender_ready = get_input_path(active_job, "tender") is not None
    boq_ready = get_input_path(active_job, "boq") is not None
    database_ready = get_input_path(active_job, "database") is not None or Path(runtime.default_database_path).exists()

    action_cols = st.columns(5)
    action_specs = [
        ("analyze_tender", "Analyze Tender", not tender_ready, "Tender input is required."),
        ("draft_boq", "Generate Draft BOQ", not tender_ready, "Tender input is required."),
        ("gap_check", "Run Gap Check", not tender_ready, "Tender input is required. BOQ is optional."),
        ("tender_price", "Run Tender -> Pricing", not (tender_ready and database_ready), "Tender input and a resolved database are required."),
        ("boq_price", "Price BOQ Only", not (boq_ready and database_ready), "BOQ and a resolved database are required."),
    ]
    for index, (action_key, label, disabled, help_text) in enumerate(action_specs):
        if action_cols[index].button(label, key=f"workspace_action_{action_key}_{active_job.job_id}", disabled=disabled or active_job.archived, help=help_text):
            try:
                updated_job = _run_action(runtime, active_job, action_key, title_override, threshold, apply_rates, current_operator)
                set_active_job_id(st.session_state, updated_job.job_id)
                st.success(f"{label} completed. Prior versions were kept.")
                st.rerun()
            except Exception as exc:
                st.error(safe_error_message(exc))

    if active_job.archived:
        st.warning("This job is archived. Restore it before running new actions.")
    if not tender_ready:
        st.info("Add a tender input to run tender analysis, draft BOQ, gap check, or tender -> pricing.")
    if not database_ready:
        if runtime.app_mode == "production":
            st.info("A released production database snapshot is not available yet. Ask the owner/admin to publish one in the admin app.")
        else:
            st.info("Add a database workbook before running pricing actions.")
    if not boq_ready:
        st.caption("No BOQ saved yet. Gap Check will run in review-only mode, and Tender -> Pricing can still run in tender-only mode.")

    _render_step_status(active_job)
    _render_artifacts(runtime, active_job, title_override, threshold, apply_rates, current_operator)

    with st.expander("Action History"):
        if not active_job.action_history:
            st.caption("No action history yet.")
        for entry in reversed(active_job.action_history):
            st.write(
                {
                    "timestamp": entry.get("timestamp", ""),
                    "action": entry.get("action", ""),
                    "status": entry.get("status", ""),
                    "operator_name": entry.get("operator_name", ""),
                    "message": entry.get("message", ""),
                }
            )
