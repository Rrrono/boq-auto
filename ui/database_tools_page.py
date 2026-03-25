"""Database tools Streamlit page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ingestion import (
    build_buildup_input_row,
    build_rate_library_row,
    deduplicate_database,
    generate_review_report,
    import_priced_boq,
    import_structured_rows,
    merge_reviewed_candidates,
    normalize_database_units,
    preview_priced_boq_import,
    promote_approved_candidates,
)

from .helpers import create_work_dir, read_binary, resolve_input_file, safe_error_message


def render(runtime) -> None:
    """Render the database tools page."""

    st.header("Database Tools")
    st.write("Private admin tools for maintaining the training/master database and review workflow.")

    use_master_db = st.checkbox("Use configured master/training database", value=True, key="db_tools_use_master")
    uploaded_db = st.file_uploader("Database workbook override", type=["xlsx", "xlsm"], key="db_tools_upload", disabled=use_master_db)
    existing_db_path = st.text_input(
        "Or use existing database path",
        value=runtime.master_database_path,
        key="db_tools_path",
        disabled=use_master_db,
    )
    st.caption("Admin actions below can update the selected training database. They are not shown in the staff production app.")

    action = st.selectbox(
        "Action",
        [
            "Validate database",
            "Normalize units",
            "Deduplicate database",
            "Generate review report",
            "Merge reviewed candidates",
            "Promote approved candidates",
            "Import structured rows",
            "Import priced BOQ",
        ],
    )
    dedupe_sheet = st.text_input("Deduplicate sheet", value="RateLibrary", disabled=action != "Deduplicate database")
    reviewer_name = st.text_input("Reviewer name", value=str(st.session_state.get("operator_name", "")).strip() or "Admin", disabled=action != "Merge reviewed candidates")

    import_target = st.selectbox("Import target", ["RateLibrary", "BuildUpInputs"], disabled=action != "Import structured rows")
    import_uploaded = st.file_uploader("Import table", type=["csv", "xlsx", "xlsm"], key="db_tools_import_upload", disabled=action != "Import structured rows")
    import_existing_path = st.text_input("Or use existing import file path", value="", key="db_tools_import_path", disabled=action != "Import structured rows")
    import_sheet_name = st.text_input("Import sheet name (optional)", value="", disabled=action != "Import structured rows")
    import_section = st.text_input("Default section", value="", disabled=action != "Import structured rows" or import_target != "RateLibrary")
    import_region = st.text_input("Default region", value=runtime.config.default_region, disabled=action != "Import structured rows")
    import_source = st.text_input("Default source label", value="Admin Import", disabled=action != "Import structured rows")
    priced_boq_uploaded = st.file_uploader("Priced BOQ file", type=["xlsx", "xlsm", "pdf"], key="db_tools_priced_boq_upload", disabled=action != "Import priced BOQ")
    priced_boq_existing_path = st.text_input("Or use existing priced BOQ path", value="", key="db_tools_priced_boq_path", disabled=action != "Import priced BOQ")
    priced_boq_region = st.text_input("Priced BOQ region", value=runtime.config.default_region, key="db_tools_priced_boq_region", disabled=action != "Import priced BOQ")
    priced_boq_source = st.text_input("Priced BOQ source label", value="Priced BOQ Import", key="db_tools_priced_boq_source", disabled=action != "Import priced BOQ")
    priced_boq_ai_assist = st.checkbox(
        "Use AI-assisted BOQ alias suggestions when available",
        value=bool(runtime.config.get("ai.admin_ingestion_assist", False)),
        key="db_tools_priced_boq_ai_assist",
        disabled=action != "Import priced BOQ",
    )
    preview_key = "db_tools_priced_boq_preview"

    mutating_actions = {
        "Normalize units",
        "Deduplicate database",
        "Generate review report",
        "Merge reviewed candidates",
        "Promote approved candidates",
        "Import structured rows",
        "Import priced BOQ",
    }
    if action != "Import priced BOQ":
        st.session_state.pop(preview_key, None)
    confirm_mutation = st.checkbox(
        "I understand mutating actions can update the selected training database",
        value=False,
        key="db_tools_confirm_mutation",
        disabled=action not in mutating_actions,
    )

    if action == "Import priced BOQ" and st.button("Preview priced BOQ extraction"):
        try:
            work_dir = create_work_dir(runtime.config)
            priced_boq_path = resolve_input_file(priced_boq_uploaded, priced_boq_existing_path, work_dir)
            preview = preview_priced_boq_import(
                db_path=str(db_path),
                boq_path=str(priced_boq_path),
                region=priced_boq_region.strip(),
                source_label=priced_boq_source.strip() or None,
                config=runtime.config,
                ai_assist=priced_boq_ai_assist,
            )
            st.session_state[preview_key] = preview
        except Exception as exc:
            st.session_state.pop(preview_key, None)
            st.error(safe_error_message(exc))

    preview = st.session_state.get(preview_key) if action == "Import priced BOQ" else None
    if preview is not None:
        st.info(
            f"Preview found {preview.total_extracted} priced BOQ row(s) for {preview.region}. "
            f"Skipped {preview.skipped_missing_rate} without rate and {preview.skipped_missing_unit} without unit."
        )
        if preview.append_count or preview.candidate_count or preview.duplicate_count:
            decision_cols = st.columns(3)
            decision_cols[0].metric("Would append", preview.append_count)
            decision_cols[1].metric("Would create candidates", preview.candidate_count)
            decision_cols[2].metric("Would skip as duplicates", preview.duplicate_count)
        if preview.notes:
            st.write(preview.notes)
        if preview.extracted_rows:
            st.caption("Sample extracted priced BOQ rows")
            st.dataframe(preview.extracted_rows[:50], use_container_width=True)
        if preview.append_preview:
            st.caption("Rows expected to append cleanly")
            st.dataframe(preview.append_preview[:50], use_container_width=True)
        if preview.candidate_preview:
            st.caption("Rows expected to route to CandidateMatches")
            st.dataframe(preview.candidate_preview[:50], use_container_width=True)
        if preview.duplicate_preview:
            st.caption("Rows expected to be skipped as same-rate duplicates")
            st.dataframe(preview.duplicate_preview[:50], use_container_width=True)
        if preview.alias_preview:
            st.caption("Style-learning preview")
            st.dataframe(preview.alias_preview[:50], use_container_width=True)

    if st.button("Run Database Tool", type="primary"):
        try:
            work_dir = create_work_dir(runtime.config)
            if use_master_db:
                db_path = Path(runtime.master_database_path)
            else:
                db_path = resolve_input_file(uploaded_db, existing_db_path, work_dir)
            if action in mutating_actions and not confirm_mutation:
                raise ValueError("Please confirm that you want to update the selected training database.")
            if not db_path.exists():
                raise FileNotFoundError(f"Database workbook not found: {db_path}")
            if action == "Validate database":
                errors = runtime.pricing_engine.validate_database(str(db_path))
                if errors:
                    st.error("Validation found issues.")
                    st.write(errors)
                else:
                    st.success("Database validation passed.")
                st.download_button(
                    "Download checked database copy",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            elif action == "Normalize units":
                summary = normalize_database_units(str(db_path))
                st.success(f"Normalized {summary.normalized_rows} field(s).")
                st.download_button(
                    "Download normalized database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            elif action == "Deduplicate database":
                summary = deduplicate_database(str(db_path), dedupe_sheet)
                st.success(f"Deactivated {summary.skipped_duplicates} duplicate row(s) in {dedupe_sheet}.")
                st.download_button(
                    "Download deduplicated database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            elif action == "Generate review report":
                json_path = work_dir / "review_report.json"
                summary = generate_review_report(str(db_path), str(json_path))
                st.success(f"Generated Candidate Review sheet with {summary.report_rows} row(s).")
                st.download_button(
                    "Download review-ready database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                if json_path.exists():
                    st.download_button(
                        "Download training JSON",
                        data=read_binary(json_path),
                        file_name=json_path.name,
                        mime="application/json",
                    )
            elif action == "Merge reviewed candidates":
                summary = merge_reviewed_candidates(str(db_path), reviewer_name or None)
                st.success(f"Merged {summary.reviewed} reviewed candidate row(s) back into CandidateMatches.")
                st.download_button(
                    "Download merged database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            elif action == "Promote approved candidates":
                json_path = work_dir / "promotion_log.json"
                summary = promote_approved_candidates(str(db_path), str(json_path))
                st.success(f"Promoted {summary.promoted} approved candidate row(s).")
                st.download_button(
                    "Download promoted database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                if json_path.exists():
                    st.download_button(
                        "Download promotion JSON",
                        data=read_binary(json_path),
                        file_name=json_path.name,
                        mime="application/json",
                    )
            elif action == "Import priced BOQ":
                priced_boq_path = resolve_input_file(priced_boq_uploaded, priced_boq_existing_path, work_dir)
                summary = import_priced_boq(
                    db_path=str(db_path),
                    boq_path=str(priced_boq_path),
                    region=priced_boq_region.strip(),
                    source_label=priced_boq_source.strip() or None,
                    config=runtime.config,
                    ai_assist=priced_boq_ai_assist,
                )
                st.success(
                    f"Imported {summary.appended} priced BOQ row(s), created {summary.candidates_created} candidate review row(s), and skipped {summary.skipped_duplicates} duplicate row(s)."
                )
                if summary.notes:
                    st.write(summary.notes)
                st.download_button(
                    "Download updated database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                import_path = resolve_input_file(import_uploaded, import_existing_path, work_dir)
                mapper = build_rate_library_row if import_target == "RateLibrary" else build_buildup_input_row
                defaults = {
                    "section": import_section.strip(),
                    "region": import_region.strip(),
                    "source": import_source.strip(),
                }
                summary = import_structured_rows(
                    db_path=str(db_path),
                    input_path=str(import_path),
                    target_sheet=import_target,
                    mapper=mapper,
                    defaults=defaults,
                    source_sheet=import_sheet_name.strip() or None,
                )
                st.success(
                    f"Imported {summary.appended} row(s), created {summary.candidates_created} candidate review row(s), and skipped {summary.skipped_duplicates} duplicate row(s)."
                )
                st.download_button(
                    "Download updated database",
                    data=read_binary(db_path),
                    file_name=db_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except Exception as exc:
            st.error(safe_error_message(exc))
