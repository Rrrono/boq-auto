"""Admin and logs Streamlit page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src import __version__
from src.release_manager import release_summary

from .helpers import summarize_config, tail_log


def render(runtime, show_admin_controls: bool = True) -> None:
    """Render the admin and logs page."""

    st.header("Admin / Logs" if show_admin_controls else "System / Logs")
    st.write(
        "Full support, config, and release diagnostics."
        if show_admin_controls
        else "Operational diagnostics and safe system visibility for the office team."
    )

    st.subheader("System Overview")
    st.json(
        {
            "version": __version__,
            "app_mode": runtime.app_mode,
            "default_region": runtime.config.default_region,
            "default_currency": runtime.config.default_currency,
            "log_file": runtime.config.log_file,
            "database_dir": runtime.config.database_dir,
            "boq_dir": runtime.config.boq_dir,
            "output_dir": runtime.config.output_dir,
            "resolved_database_path": runtime.default_database_path,
        }
    )

    st.subheader("Database Release Summary")
    st.json(release_summary(runtime.config))

    st.subheader("Current Config Summary")
    st.json(summarize_config(runtime.config))

    st.subheader("Recent Log Preview")
    preview_lines = st.slider(
        "Preview lines",
        min_value=20,
        max_value=200,
        value=int(runtime.config.get("ui.log_preview_lines", 80)),
        step=20,
    )
    st.code(tail_log(runtime.config.log_file, preview_lines), language="text")

    st.subheader("Key Paths")
    st.write(
        {
            "project_root": str(Path.cwd()),
            "database_dir": str(Path(runtime.config.database_dir)),
            "boq_dir": str(Path(runtime.config.boq_dir)),
            "output_dir": str(Path(runtime.config.output_dir)),
            "workspace_jobs_dir": str(Path(runtime.config.get("ui.workspace_root", "workspace/jobs"))),
            "logs_dir": str(Path(runtime.config.log_file).parent),
        }
    )

    if not show_admin_controls:
        st.caption("Database mutation, training, promotion, and release controls are intentionally kept in the private admin app.")
