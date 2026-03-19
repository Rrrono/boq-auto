"""Admin-only home page for BOQ AUTO."""

from __future__ import annotations

import streamlit as st

from src.release_manager import release_summary
from ui.job_manager import get_active_job


def render(runtime) -> None:
    """Render the admin home page."""

    st.header("BOQ AUTO Admin / Training")
    st.write("Private owner/admin workspace for training data, release control, and governed operational support.")
    st.warning("Use this app for database maintenance, review promotion, and release decisions. Colleagues should use the production app for daily work.")
    st.json(release_summary(runtime.config))

    active_job = get_active_job(runtime.config, st.session_state)
    if active_job:
        st.success(f"Active workspace job: {active_job.title} [{active_job.job_id}]")

    st.markdown(
        """
Admin app responsibilities:
- maintain the training/master database
- review and promote candidate learning
- prepare released production database snapshots
- support operational teams without exposing training controls in the staff app
"""
    )
