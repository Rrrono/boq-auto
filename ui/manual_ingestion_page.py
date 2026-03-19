"""Admin UI for manual cost PDF ingestion into the master database."""

from __future__ import annotations

from pathlib import Path
import inspect
from typing import Any

import pandas as pd
import streamlit as st

from src.ai.embedding_provider import HashEmbeddingProvider, OpenAIEmbeddingProvider
from src.cost_schema import CostDatabase, composed_embedding_text, schema_database_path
from src.release_manager import master_database_path, release_summary
from ui.helpers import create_work_dir, safe_error_message, save_uploaded_file

try:
    from src.manual_parser import ManualItem, ingest_manual_to_database, load_manual_pdf, parse_manual_text
    MANUAL_PARSER_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - defensive until parser lands
    ManualItem = None
    ingest_manual_to_database = None
    load_manual_pdf = None
    parse_manual_text = None
    MANUAL_PARSER_IMPORT_ERROR = exc


DISPLAY_COLUMNS = ["Select", "Code", "Item Name", "Unit", "Description"]


def _ensure_state() -> None:
    st.session_state.setdefault("parsed_items", [])
    st.session_state.setdefault("filtered_items", [])
    st.session_state.setdefault("last_uploaded_file", "")
    st.session_state.setdefault("last_uploaded_signature", "")
    st.session_state.setdefault("admin_ai_enabled", False)
    st.session_state.setdefault("admin_ingestion_ai_assist", False)


def _get_value(item: Any, *names: str) -> str:
    for name in names:
        if isinstance(item, dict) and name in item:
            value = item.get(name)
            if value not in (None, ""):
                return str(value)
        if hasattr(item, name):
            value = getattr(item, name)
            if value not in (None, ""):
                return str(value)
    return ""


def _coerce_row(item: Any, row_id: int) -> dict[str, Any]:
    return {
        "_row_id": row_id,
        "Select": True,
        "Code": _get_value(item, "code", "item_code"),
        "Item Name": _get_value(item, "item_name", "name", "title"),
        "Unit": _get_value(item, "unit", "uom"),
        "Description": _get_value(item, "description", "details", "notes"),
    }


def _manual_item_from_row(row: dict[str, Any]) -> Any:
    if ManualItem is None:
        raise RuntimeError("src.manual_parser is not available.")

    payload = {
        "code": str(row.get("Code") or "").strip(),
        "item_code": str(row.get("Code") or "").strip(),
        "item_name": str(row.get("Item Name") or "").strip(),
        "name": str(row.get("Item Name") or "").strip(),
        "title": str(row.get("Item Name") or "").strip(),
        "unit": str(row.get("Unit") or "").strip(),
        "uom": str(row.get("Unit") or "").strip(),
        "description": str(row.get("Description") or "").strip(),
        "details": str(row.get("Description") or "").strip(),
        "notes": str(row.get("Description") or "").strip(),
    }
    signature = inspect.signature(ManualItem)
    kwargs = {}
    for parameter_name in signature.parameters:
        if parameter_name == "self":
            continue
        if parameter_name in payload:
            kwargs[parameter_name] = payload[parameter_name]
    return ManualItem(**kwargs)


def _apply_filters(rows: list[dict[str, Any]], search_text: str, unit_value: str, code_prefix: str) -> list[dict[str, Any]]:
    query = search_text.strip().lower()
    prefix = code_prefix.strip().lower()
    filtered: list[dict[str, Any]] = []
    for row in rows:
        haystack = f"{row.get('Item Name', '')} {row.get('Description', '')}".lower()
        if query and query not in haystack:
            continue
        if unit_value and unit_value != "All" and str(row.get("Unit") or "").strip() != unit_value:
            continue
        if prefix and not str(row.get("Code") or "").strip().lower().startswith(prefix):
            continue
        filtered.append(dict(row))
    return filtered


def _update_master_rows(edited_df: pd.DataFrame, parsed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed_by_id = {int(row["_row_id"]): dict(row) for row in parsed_rows}
    for row_id, values in edited_df.iterrows():
        row_payload = values.to_dict()
        row_payload["_row_id"] = int(row_id)
        parsed_by_id[int(row_id)] = row_payload
    return [parsed_by_id[row_id] for row_id in sorted(parsed_by_id)]


def render(runtime) -> None:
    """Render the admin manual ingestion page."""

    _ensure_state()

    st.header("Manual Cost Ingestion")
    st.write("Upload a cost manual PDF, parse it into structured items, review the extraction, and explicitly commit approved rows into the master database.")

    if MANUAL_PARSER_IMPORT_ERROR is not None:
        st.error(f"Manual parser dependency is not available: {MANUAL_PARSER_IMPORT_ERROR}")
        st.info("Add `src.manual_parser` before using this admin page.")
        return

    ai_enabled = st.checkbox(
        "Enable AI matching features for admin tooling",
        value=bool(st.session_state.get("admin_ai_enabled", runtime.config.get("ai.enabled", False))),
        key="manual_ingestion_ai_toggle",
    )
    st.session_state["admin_ai_enabled"] = ai_enabled
    ai_ingestion_assist = st.checkbox(
        "Use AI-assisted alias/category suggestions during ingestion",
        value=bool(st.session_state.get("admin_ingestion_ai_assist", runtime.config.get("ai.admin_ingestion_assist", False))),
        key="manual_ingestion_ai_assist_toggle",
    )
    st.session_state["admin_ingestion_ai_assist"] = ai_ingestion_assist

    upload = st.file_uploader("Upload Cost Manual", type=["pdf"], key="manual_ingestion_upload")
    if upload is not None:
        upload_signature = f"{upload.name}:{upload.size}"
        if st.session_state.get("last_uploaded_signature") != upload_signature:
            work_dir = create_work_dir(runtime.config)
            saved_path = save_uploaded_file(upload, work_dir)
            st.session_state["last_uploaded_file"] = str(saved_path)
            st.session_state["last_uploaded_signature"] = upload_signature
            st.session_state["parsed_items"] = []
            st.session_state["filtered_items"] = []
        st.caption(f"Temporary file: {st.session_state['last_uploaded_file']}")

    if st.button("Parse Manual", type="primary", key="manual_ingestion_parse"):
        if not st.session_state.get("last_uploaded_file"):
            st.warning("Upload a PDF cost manual first.")
        else:
            try:
                manual_path = st.session_state["last_uploaded_file"]
                manual_lines = load_manual_pdf(manual_path)
                parsed_items = parse_manual_text(manual_lines)
                rows = [_coerce_row(item, row_id=index) for index, item in enumerate(parsed_items)]
                st.session_state["parsed_items"] = rows
                st.session_state["filtered_items"] = list(rows)
                st.success(f"Parsed {len(rows)} item(s) from the uploaded manual.")
            except Exception as exc:
                st.error(safe_error_message(exc))

    parsed_rows = list(st.session_state.get("parsed_items", []))
    db_path = Path(master_database_path(runtime.config))
    schema_path = schema_database_path(db_path)

    if not parsed_rows:
        st.warning("No items parsed yet. Upload a manual PDF and click Parse Manual.")
    else:
        with st.expander("Filters", expanded=True):
            search_text = st.text_input("Search", value="", key="manual_ingestion_search", help="Filters item name and description.")
            unit_options = ["All"] + sorted({str(row.get("Unit") or "").strip() for row in parsed_rows if str(row.get("Unit") or "").strip()})
            unit_value = st.selectbox("Unit filter", options=unit_options, key="manual_ingestion_unit_filter")
            code_prefix = st.text_input("Code prefix filter", value="", key="manual_ingestion_code_prefix")

        filtered_rows = _apply_filters(parsed_rows, search_text, unit_value, code_prefix)
        st.session_state["filtered_items"] = filtered_rows

        total_count = len(parsed_rows)
        filtered_count = len(filtered_rows)
        selected_total = sum(1 for row in parsed_rows if bool(row.get("Select", True)))
        metric_cols = st.columns(3)
        metric_cols[0].metric("Total parsed items", total_count)
        metric_cols[1].metric("Selected items", selected_total)
        metric_cols[2].metric("Filtered items", filtered_count)

        with st.expander("Preview Parsed Items", expanded=True):
            if not filtered_rows:
                st.info("No parsed items match the current filters.")
            else:
                editor_df = pd.DataFrame(filtered_rows).set_index("_row_id")[DISPLAY_COLUMNS]
                edited_df = st.data_editor(
                    editor_df,
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "Select": st.column_config.CheckboxColumn(default=True),
                        "Code": st.column_config.TextColumn(),
                        "Item Name": st.column_config.TextColumn(),
                        "Unit": st.column_config.TextColumn(),
                        "Description": st.column_config.TextColumn(width="large"),
                    },
                    key="manual_ingestion_editor",
                )
                updated_rows = _update_master_rows(edited_df, parsed_rows)
                st.session_state["parsed_items"] = updated_rows
                st.session_state["filtered_items"] = _apply_filters(updated_rows, search_text, unit_value, code_prefix)

    with st.expander("Commit Section", expanded=True):
        summary = release_summary(runtime.config)
        st.caption(f"Master database path: {db_path}")
        st.caption(f"Normalized schema sidecar: {schema_path}")
        st.caption(f"Current production release (read-only reference): {summary.get('current_production_database_path', '')}")
        confirm_commit = st.checkbox("I confirm these items are clean and reviewed", key="manual_ingestion_confirm")

        if st.button("Commit Selected to Database", type="primary", key="manual_ingestion_commit"):
            try:
                if not st.session_state.get("parsed_items"):
                    st.warning("No parsed items are available to commit.")
                    return
                if not db_path.exists():
                    st.error(f"Master database path is missing: {db_path}")
                    return
                if not confirm_commit:
                    st.warning("Confirm that the items are clean and reviewed before committing.")
                    return

                selected_rows = [row for row in st.session_state["parsed_items"] if bool(row.get("Select", True))]
                if not selected_rows:
                    st.info("No rows are selected for commit.")
                    return

                manual_items = [_manual_item_from_row(row) for row in selected_rows]
                ingest_manual_to_database(
                    manual_items,
                    str(db_path),
                    source_name=Path(st.session_state.get("last_uploaded_file") or "manual_review").stem,
                    source_file=str(st.session_state.get("last_uploaded_file") or ""),
                    ai_enhance=ai_ingestion_assist,
                )
                st.success(f"Committed {len(manual_items)} reviewed item(s) into the master database.")
            except Exception as exc:
                st.error(safe_error_message(exc))

    with st.expander("AI Controls", expanded=False):
        st.caption("These controls are admin-only. Production releases remain read-only.")
        if st.button("Generate Embeddings For Schema Database", key="manual_ingestion_generate_embeddings", disabled=not ai_enabled):
            try:
                repository = CostDatabase(schema_path)
                items = repository.fetch_items()
                provider_name = str(runtime.config.get("ai.provider", "disabled")).strip().lower()
                provider = OpenAIEmbeddingProvider(model=str(runtime.config.get("ai.embedding_model", "text-embedding-3-small"))) if provider_name == "openai" else HashEmbeddingProvider()
                generated = 0
                for item in items:
                    embedding = provider.embed(composed_embedding_text(item))
                    if not embedding:
                        continue
                    repository.save_embedding(item.id, embedding, getattr(provider, "model_name", "unknown"))
                    generated += 1
                st.success(f"Generated embeddings for {generated} item(s).")
            except Exception as exc:
                st.error(safe_error_message(exc))
        if not ai_enabled:
            st.info("AI tooling is off. Rule mode remains fully available.")

    with st.expander("Ingestion Logs", expanded=False):
        try:
            repository = CostDatabase(schema_path)
            logs = repository.fetch_ingestion_logs()
            if not logs:
                st.caption("No ingestion logs recorded yet.")
            else:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "created_at": log.created_at,
                                "source_id": log.source_id,
                                "status": log.status,
                                "message": log.message,
                            }
                            for log in logs
                        ]
                    ),
                    use_container_width=True,
                )
        except Exception as exc:
            st.error(safe_error_message(exc))
