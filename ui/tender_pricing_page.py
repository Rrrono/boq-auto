"""Tender-to-pricing Streamlit page."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.cost_schema import schema_database_path
from src.matching_engine import log_match_feedback

from .helpers import create_work_dir, read_binary, read_json, resolve_input_file, safe_error_message
from .job_manager import get_active_job, run_tender_pricing


def _render_confidence_preview(runtime, audit_json_path: Path, db_path: Path, key_suffix: str) -> None:
    if not audit_json_path.exists():
        return
    payload = read_json(audit_json_path)
    results = list(payload.get("results", []))
    if not results:
        return
    preview = pd.DataFrame(
        [
            {
                "description": row.get("description", ""),
                "matched_item_code": row.get("matched_item_code", ""),
                "matched_description": row.get("matched_description", ""),
                "decision": row.get("decision", ""),
                "confidence_score": row.get("confidence_score", 0),
            }
            for row in results[:25]
        ]
    )
    st.subheader("Match Confidence Preview")
    st.dataframe(preview, use_container_width=True)

    if runtime.app_mode != "admin":
        return
    feedback_options = {
        f"{row.get('description', '')} -> {row.get('matched_item_code', '')}": row
        for row in results
        if row.get("matched_item_code")
    }
    if not feedback_options:
        return
    with st.expander("Log Match Feedback", expanded=False):
        selected_label = st.selectbox("Reviewed match", options=list(feedback_options.keys()), key=f"tender_feedback_row_{key_suffix}")
        selected_row = feedback_options[selected_label]
        rejected_text = st.text_input("Rejected item ids (comma separated)", value="", key=f"tender_feedback_rejected_{key_suffix}")
        if st.button("Save Feedback", key=f"tender_feedback_save_{key_suffix}"):
            log_match_feedback(
                str(schema_database_path(db_path)),
                selected_row.get("description", ""),
                str(selected_row.get("matched_item_code", "")),
                [value.strip() for value in rejected_text.split(",") if value.strip()],
            )
            st.success("Match feedback logged for future tuning.")


def render(runtime) -> None:
    """Render the integrated tender-to-pricing page."""

    st.header("Tender -> Pricing")
    st.write("Run the integrated review-first workflow from tender input into pricing.")
    mode_options = ["rule", "hybrid", "ai"]
    default_mode = str(runtime.config.get("matching.mode", "rule")).strip().lower()
    default_mode_index = mode_options.index(default_mode) if default_mode in mode_options else 0
    if runtime.app_mode == "production":
        st.caption(f"Production pricing uses the current released database snapshot by default: {runtime.default_database_path}")

    active_job = get_active_job(runtime.config, st.session_state)
    if active_job is not None:
        st.info(f"Using active workspace job: {active_job.title} [{active_job.job_id}]")
        if active_job.archived:
            st.warning("This workspace job is archived. Restore it in Workspace / Jobs before running new actions.")
            return
        operator_name = str(st.session_state.get("operator_name", "")).strip() or active_job.operator_name or "Office User"
        tender_title = st.text_input("Tender title override", value=active_job.title, key=f"job_tender_price_title_{active_job.job_id}")
        matching_mode = st.selectbox("Matching mode", options=mode_options, index=default_mode_index, key=f"job_tender_price_matching_mode_{active_job.job_id}")
        threshold = st.number_input(
            "Matching threshold",
            min_value=0.0,
            max_value=100.0,
            value=float(runtime.config.get("matching.threshold", 78)),
            key=f"job_tender_price_threshold_{active_job.job_id}",
        )
        apply_rates = st.checkbox(
            "Apply rates into priced workbook",
            value=bool(runtime.config.get("processing.apply_rates", False)),
            key=f"job_tender_price_apply_{active_job.job_id}",
        )
        if st.button("Run Tender -> Pricing For Active Job", type="primary", key=f"job_tender_price_run_{active_job.job_id}"):
            try:
                updated_job = run_tender_pricing(runtime, active_job, threshold, apply_rates, tender_title or None, operator_name, matching_mode=matching_mode)
                latest = next((artifact for artifact in updated_job.artifacts if artifact.artifact_type == "tender_price_workbook"), None)
                audit_artifact = next((artifact for artifact in updated_job.artifacts if artifact.artifact_type == "tender_price_audit_json"), None)
                st.success("Tender -> Pricing completed and saved as a new workspace artifact version.")
                if latest and Path(latest.latest_path).exists():
                    st.download_button(
                        "Download latest integrated workbook",
                        data=read_binary(latest.latest_path),
                        file_name=Path(latest.latest_path).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                if audit_artifact and Path(audit_artifact.latest_path).exists():
                    resolved_db_path = Path(runtime.default_database_path if runtime.app_mode == "production" else active_job.inputs.get("database") or runtime.default_database_path)
                    _render_confidence_preview(runtime, Path(audit_artifact.latest_path), resolved_db_path, f"job_{active_job.job_id}")
            except Exception as exc:
                st.error(safe_error_message(exc))
        if runtime.app_mode == "production":
            st.caption("Saved tender and BOQ files are reused from the active workspace job, and pricing resolves the current released production database automatically.")
        else:
            st.caption("Saved tender, BOQ, and database files are reused from the active workspace job.")
        return

    uploaded_tender = st.file_uploader("Tender input", type=["pdf", "txt", "md", "csv", "xlsx", "xlsm"], key="tender_price_tender")
    existing_tender_path = st.text_input("Or use existing tender path", value="tender/demo_tender_notice.txt")

    use_boq = st.checkbox("Use an existing BOQ workbook in this run", value=True)
    uploaded_boq = st.file_uploader("Optional BOQ workbook", type=["xlsx", "xlsm"], key="tender_price_boq", disabled=not use_boq)
    existing_boq_path = st.text_input("Optional existing BOQ path", value="boq/demo_boq.xlsx", disabled=not use_boq)

    uploaded_db = None
    existing_db_path = runtime.default_database_path
    if runtime.app_mode == "admin":
        uploaded_db = st.file_uploader("Database workbook", type=["xlsx", "xlsm"], key="tender_price_db")
        existing_db_path = st.text_input("Or use existing database path", value=runtime.default_database_path)
    else:
        st.caption(f"Resolved production database: {runtime.default_database_path}")

    tender_title = st.text_input("Tender title override", value="")
    region = st.text_input("Region", value=runtime.config.default_region)
    matching_mode = st.selectbox("Matching mode", options=mode_options, index=default_mode_index, key="tender_price_matching_mode")
    threshold = st.number_input("Matching threshold", min_value=0.0, max_value=100.0, value=float(runtime.config.get("matching.threshold", 78)), key="tender_price_threshold")
    apply_rates = st.checkbox("Apply rates into priced workbook", value=bool(runtime.config.get("processing.apply_rates", False)), key="tender_price_apply")

    if st.button("Run Tender -> Pricing", type="primary"):
        work_dir = create_work_dir(runtime.config)
        try:
            tender_path = resolve_input_file(uploaded_tender, existing_tender_path, work_dir)
            if runtime.app_mode == "admin":
                db_path = resolve_input_file(uploaded_db, existing_db_path, work_dir)
            else:
                db_path = Path(runtime.default_database_path)
                if not db_path.exists():
                    raise FileNotFoundError(f"Production database snapshot not found: {db_path}")
            boq_path = None
            if use_boq and (uploaded_boq is not None or existing_boq_path.strip()):
                try:
                    boq_path = resolve_input_file(uploaded_boq, existing_boq_path, work_dir)
                except Exception:
                    boq_path = None
            out_path = work_dir / f"{Path(tender_path).stem}_tender_priced.xlsx"
            json_path = work_dir / f"{Path(tender_path).stem}_tender_priced.json"
            with st.spinner("Running integrated tender-to-pricing workflow..."):
                artifacts = runtime.tender_to_price_runner.run(
                    input_path=str(tender_path),
                    db_path=str(db_path),
                    output_path=str(out_path),
                    boq_path=str(boq_path) if boq_path else None,
                    region=region,
                    threshold=threshold,
                    apply_rates=apply_rates,
                    title_override=tender_title or None,
                    json_path=str(json_path),
                    matching_mode=matching_mode,
                )
            st.success("Integrated tender-to-pricing workflow completed.")
            st.json(
                {
                    "handoff_rows": len(artifacts.pricing_handoff_rows),
                    "priced_items": artifacts.pricing_artifacts.processed if artifacts.pricing_artifacts else 0,
                    "flagged": artifacts.pricing_artifacts.flagged if artifacts.pricing_artifacts else 0,
                }
            )
            st.download_button(
                "Download integrated workbook",
                data=read_binary(artifacts.output_workbook),
                file_name=artifacts.output_workbook.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            if artifacts.output_json and artifacts.output_json.exists():
                st.download_button(
                    "Download integrated JSON",
                    data=read_binary(artifacts.output_json),
                    file_name=artifacts.output_json.name,
                    mime="application/json",
                )
            if artifacts.pricing_artifacts and artifacts.pricing_artifacts.audit_json and artifacts.pricing_artifacts.audit_json.exists():
                _render_confidence_preview(runtime, artifacts.pricing_artifacts.audit_json, Path(db_path), "adhoc")
        except Exception as exc:
            st.error(safe_error_message(exc))
