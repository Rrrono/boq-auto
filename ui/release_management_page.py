"""Admin-only release management page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.release_manager import create_release_snapshot, list_releases, release_summary, set_current_release
from ui.helpers import read_binary, safe_error_message


def render(runtime) -> None:
    """Render the database release management page."""

    st.header("Release Management")
    st.write("Create and manage released production database snapshots without overwriting earlier releases.")

    operator_name = str(st.session_state.get("operator_name", "")).strip() or "Admin"
    st.caption(f"Current operator: {operator_name}")
    st.json(release_summary(runtime.config))

    notes = st.text_area("Release notes", value="", key="release_notes")
    if st.button("Create New Production Release", type="primary", key="release_create"):
        try:
            record = create_release_snapshot(runtime.config, operator_name, notes)
            runtime.logger.info("database_release_created | operator=%s | release_id=%s | path=%s", operator_name, record.release_id, record.path)
            st.success(f"Created release {record.release_id} and set it as the current production snapshot.")
            st.rerun()
        except Exception as exc:
            st.error(safe_error_message(exc))

    st.subheader("Released Snapshots")
    releases = list_releases(runtime.config)
    if not releases:
        st.info("No production releases found yet. Create the first release from the current master database.")
        return

    options = {record.release_id: record for record in releases}
    selected_id = st.selectbox(
        "Select release",
        options=[record.release_id for record in releases],
        format_func=lambda value: f"{value} ({'current' if options[value].is_current else 'available'})",
        key="release_select",
    )
    selected = options[selected_id]

    st.write(
        {
            "release_id": selected.release_id,
            "created_at": selected.created_at,
            "created_by": selected.created_by,
            "notes": selected.notes,
            "path": selected.path,
            "is_current": selected.is_current,
        }
    )

    control_cols = st.columns(2)
    if control_cols[0].button("Set As Current Production Release", key="release_set_current", disabled=selected.is_current):
        try:
            set_current_release(runtime.config, selected.path, operator_name)
            runtime.logger.info("database_release_selected | operator=%s | release_id=%s | path=%s", operator_name, selected.release_id, selected.path)
            st.success(f"{selected.release_id} is now the active production database snapshot.")
            st.rerun()
        except Exception as exc:
            st.error(safe_error_message(exc))

    release_path = Path(selected.path)
    if release_path.exists():
        control_cols[1].download_button(
            "Download Selected Release",
            data=read_binary(release_path),
            file_name=release_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="release_download",
        )
