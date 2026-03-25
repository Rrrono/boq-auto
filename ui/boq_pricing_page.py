"""BOQ pricing Streamlit page."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import streamlit as st

from src.cost_schema import schema_database_path
from src.matching_engine import log_match_feedback

from .helpers import create_work_dir, get_current_mode_label, read_binary, read_json, resolve_input_file, safe_error_message
from .job_manager import get_active_job, run_price_boq


def _parse_alternative_item_id(option_text: str) -> str:
    raw = str(option_text or "").strip()
    if not raw:
        return ""
    return re.split(r"\s*\|\s*", raw, maxsplit=1)[0].strip()


def _render_confidence_preview(runtime, audit_json_path: Path, db_path: Path, key_suffix: str) -> None:
    if not audit_json_path.exists():
        return
    payload = read_json(audit_json_path)
    results = list(payload.get("results", []))
    actual_mode = str(payload.get("metadata", {}).get("matching_mode", "rule"))
    if not results:
        return
    st.caption(f"Matching Mode: {get_current_mode_label(runtime.config, actual_mode)}")
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
    with st.expander("Learning Feedback", expanded=False):
        for index, (selected_label, selected_row) in enumerate(feedback_options.items()):
            with st.container(border=True):
                st.write(
                    {
                        "query": selected_row.get("description", ""),
                        "current_match": selected_row.get("matched_item_code", ""),
                        "matched_description": selected_row.get("matched_description", ""),
                        "confidence_score": selected_row.get("confidence_score", 0),
                    }
                )
                alternative_options = [option for option in selected_row.get("alternate_options", []) if str(option).strip()]
                alternative_choice = st.selectbox(
                    "Select alternative match",
                    options=[""] + alternative_options,
                    key=f"pricing_feedback_alt_{key_suffix}_{index}",
                    help="Choose one of the top alternate matches when the current match is wrong.",
                )
                action_cols = st.columns(3)
                schema_path = schema_database_path(db_path)
                if action_cols[0].button("Accept Match", key=f"pricing_feedback_accept_{key_suffix}_{index}"):
                    log_match_feedback(
                        str(schema_path),
                        selected_row.get("description", ""),
                        str(selected_row.get("matched_item_code", "")),
                        "accepted",
                    )
                    st.success("Accepted match saved to the learning loop.")
                if action_cols[1].button("Reject Match", key=f"pricing_feedback_reject_{key_suffix}_{index}"):
                    log_match_feedback(
                        str(schema_path),
                        selected_row.get("description", ""),
                        str(selected_row.get("matched_item_code", "")),
                        "rejected",
                    )
                    st.success("Rejected match saved to the learning loop.")
                if action_cols[2].button("Apply Alternative", key=f"pricing_feedback_correct_{key_suffix}_{index}", disabled=not alternative_choice):
                    alternative_item_id = _parse_alternative_item_id(alternative_choice)
                    log_match_feedback(
                        str(schema_path),
                        selected_row.get("description", ""),
                        str(selected_row.get("matched_item_code", "")),
                        "corrected",
                        alternative_item_id=alternative_item_id,
                    )
                    st.success(f"Alternative match {alternative_item_id or alternative_choice} saved to the learning loop.")


def render(runtime) -> None:
    """Render the BOQ pricing page."""

    st.header("BOQ Pricing")
    st.write("Price an Excel BOQ workbook using the existing BOQ AUTO pricing engine.")
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
        matching_mode = st.selectbox("Matching mode", options=mode_options, index=default_mode_index, key=f"job_price_matching_mode_{active_job.job_id}")
        threshold = st.number_input(
            "Matching threshold",
            min_value=0.0,
            max_value=100.0,
            value=float(runtime.config.get("matching.threshold", 78)),
            key=f"job_price_threshold_{active_job.job_id}",
        )
        apply_rates = st.checkbox(
            "Apply rates into workbook",
            value=bool(runtime.config.get("processing.apply_rates", False)),
            key=f"job_price_apply_{active_job.job_id}",
        )
        if st.button("Run BOQ Pricing For Active Job", type="primary", key=f"job_price_run_{active_job.job_id}"):
            try:
                updated_job = run_price_boq(runtime, active_job, threshold, apply_rates, operator_name, matching_mode=matching_mode)
                latest = next((artifact for artifact in updated_job.artifacts if artifact.artifact_type == "boq_price_workbook"), None)
                audit_artifact = next((artifact for artifact in updated_job.artifacts if artifact.artifact_type == "boq_price_audit_json"), None)
                st.success("BOQ pricing completed and saved as a new workspace artifact version.")
                if latest and Path(latest.latest_path).exists():
                    st.download_button(
                        "Download latest priced workbook",
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
            st.caption("Use Workspace / Jobs to change the saved BOQ once for the current job. Pricing uses the released production database automatically.")
        else:
            st.caption("Use Workspace / Jobs to change the saved BOQ or database once for the current job.")
        return

    uploaded_boq = st.file_uploader("BOQ workbook", type=["xlsx", "xlsm"], key="pricing_boq_upload")
    existing_boq_path = st.text_input("Or use existing BOQ path", value="boq/demo_boq.xlsx")

    uploaded_db = None
    existing_db_path = runtime.default_database_path
    if runtime.app_mode == "admin":
        uploaded_db = st.file_uploader("Database workbook", type=["xlsx", "xlsm"], key="pricing_db_upload")
        existing_db_path = st.text_input("Or use existing database path", value=runtime.default_database_path)
    else:
        st.caption(f"Resolved production database: {runtime.default_database_path}")

    region = st.text_input("Region", value=runtime.config.default_region)
    matching_mode = st.selectbox("Matching mode", options=mode_options, index=default_mode_index, key="pricing_matching_mode")
    threshold = st.number_input("Matching threshold", min_value=0.0, max_value=100.0, value=float(runtime.config.get("matching.threshold", 78)))
    apply_rates = st.checkbox("Apply rates into workbook", value=bool(runtime.config.get("processing.apply_rates", False)))

    if st.button("Run BOQ Pricing", type="primary"):
        work_dir = create_work_dir(runtime.config)
        try:
            boq_path = resolve_input_file(uploaded_boq, existing_boq_path, work_dir)
            if runtime.app_mode == "admin":
                db_path = resolve_input_file(uploaded_db, existing_db_path, work_dir)
            else:
                db_path = Path(runtime.default_database_path)
                if not db_path.exists():
                    raise FileNotFoundError(f"Production database snapshot not found: {db_path}")
            out_path = work_dir / f"{Path(boq_path).stem}_priced.xlsx"
            with st.spinner("Running pricing engine..."):
                artifacts = runtime.pricing_engine.price_workbook(
                    db_path=str(db_path),
                    boq_path=str(boq_path),
                    output_path=str(out_path),
                    region=region,
                    threshold=threshold,
                    apply_rates=apply_rates,
                    matching_mode=matching_mode,
                )
            st.success(f"Pricing completed. Processed {artifacts.processed} line(s).")
            st.json({"matched": artifacts.matched, "flagged": artifacts.flagged})
            st.download_button(
                "Download priced workbook",
                data=read_binary(artifacts.output_workbook),
                file_name=artifacts.output_workbook.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            if artifacts.unmatched_csv and artifacts.unmatched_csv.exists():
                st.download_button(
                    "Download unmatched CSV",
                    data=read_binary(artifacts.unmatched_csv),
                    file_name=artifacts.unmatched_csv.name,
                    mime="text/csv",
                )
            if artifacts.audit_json and artifacts.audit_json.exists():
                _render_confidence_preview(runtime, artifacts.audit_json, Path(db_path), "adhoc")
        except Exception as exc:
            st.error(safe_error_message(exc))
