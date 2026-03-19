"""Database tools Streamlit page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ingestion import (
    build_buildup_input_row,
    build_rate_library_row,
    deduplicate_database,
    generate_review_report,
    import_structured_rows,
    merge_reviewed_candidates,
    normalize_database_units,
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

    mutating_actions = {
        "Normalize units",
        "Deduplicate database",
        "Generate review report",
        "Merge reviewed candidates",
        "Promote approved candidates",
        "Import structured rows",
    }
    confirm_mutation = st.checkbox(
        "I understand mutating actions can update the selected training database",
        value=False,
        key="db_tools_confirm_mutation",
        disabled=action not in mutating_actions,
    )

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
