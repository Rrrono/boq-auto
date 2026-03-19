"""Tender analysis Streamlit page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .helpers import create_work_dir, read_binary, resolve_input_file, safe_error_message
from .job_manager import get_active_job, run_analyze_tender


def render(runtime) -> None:
    """Render the tender analysis page."""

    st.header("Tender Analysis")
    st.write("Run review-first tender analysis and download the workbook outputs.")

    active_job = get_active_job(runtime.config, st.session_state)
    if active_job is not None:
        st.info(f"Using active workspace job: {active_job.title} [{active_job.job_id}]")
        if active_job.archived:
            st.warning("This workspace job is archived. Restore it in Workspace / Jobs before running new actions.")
            return
        operator_name = str(st.session_state.get("operator_name", "")).strip() or active_job.operator_name or "Office User"
        tender_title = st.text_input("Tender title override", value=active_job.title, key=f"job_tender_analysis_title_{active_job.job_id}")
        if st.button("Run Tender Analysis For Active Job", type="primary", key=f"job_tender_analysis_run_{active_job.job_id}"):
            try:
                updated_job = run_analyze_tender(runtime, active_job, tender_title or None, operator_name)
                latest = next((artifact for artifact in updated_job.artifacts if artifact.artifact_type == "tender_analysis_workbook"), None)
                st.success("Tender analysis completed and saved as a new workspace artifact version.")
                if latest and Path(latest.latest_path).exists():
                    st.download_button(
                        "Download latest tender analysis workbook",
                        data=read_binary(latest.latest_path),
                        file_name=Path(latest.latest_path).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            except Exception as exc:
                st.error(safe_error_message(exc))
        st.caption("Need to change the tender file? Use Workspace / Jobs to replace the saved tender input once for the whole job.")
        return

    uploaded_tender = st.file_uploader(
        "Tender input",
        type=["pdf", "txt", "md", "csv", "xlsx", "xlsm"],
        help="Upload local tender PDF, text, normalized extracted text, CSV, or Excel-derived structured text.",
        key="tender_analysis_upload",
    )
    existing_tender_path = st.text_input("Or use existing tender path", value="tender/demo_tender_notice.txt")
    tender_title = st.text_input("Tender title override", value="")
    region = st.text_input("Region", value=runtime.config.default_region, help="Reserved for downstream workflow context.")

    if st.button("Run Tender Analysis", type="primary"):
        work_dir = create_work_dir(runtime.config)
        try:
            tender_path = resolve_input_file(uploaded_tender, existing_tender_path, work_dir)
            out_path = work_dir / f"{Path(tender_path).stem}_analysis.xlsx"
            json_path = work_dir / f"{Path(tender_path).stem}_analysis.json"
            with st.spinner("Running tender analysis..."):
                result = runtime.tender_workflow.analyze(
                    input_path=str(tender_path),
                    output_path=str(out_path),
                    json_path=str(json_path),
                    title_override=tender_title or None,
                )
            st.success(f"Tender analysis completed for {result.document.document_name}.")
            st.info(f"Region noted for downstream work: {region}")
            if result.summary:
                st.json(
                    {
                        "requirements": result.summary.total_requirements,
                        "scope_sections": result.summary.scope_sections,
                        "draft_suggestions": result.summary.draft_suggestions,
                        "clarifications": result.summary.clarifications,
                    }
                )
            st.download_button(
                "Download tender analysis workbook",
                data=read_binary(result.output_workbook),
                file_name=result.output_workbook.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            if result.output_json and result.output_json.exists():
                st.download_button(
                    "Download tender analysis JSON",
                    data=read_binary(result.output_json),
                    file_name=result.output_json.name,
                    mime="application/json",
                )
        except Exception as exc:
            st.error(safe_error_message(exc))
