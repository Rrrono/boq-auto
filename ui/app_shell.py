"""Shared app shell for production and admin Streamlit entry points."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from ui import admin_ai_panel, admin_page, boq_pricing_page, database_tools_page, manual_ingestion_page, tender_analysis_page, tender_pricing_page, workspace_page
from ui.helpers import AppRuntime, build_runtime
from ui.job_manager import get_active_job
from ui.release_management_page import render as render_release_management
from ui.admin_home_page import render as render_admin_home


PageRenderer = Callable[[], None]


def _render_production_home(runtime: AppRuntime) -> None:
    st.header("BOQ AUTO Production")
    st.write("Day-to-day tender review and pricing workspace for the office team.")
    st.info("This app uses the current released production database snapshot for operational pricing work.")
    st.write(
        {
            "default_region": runtime.config.default_region,
            "production_database": runtime.default_database_path,
            "workspace_jobs_dir": runtime.config.get("ui.workspace_root", "workspace/jobs"),
        }
    )
    active_job = get_active_job(runtime.config, st.session_state)
    if active_job:
        st.success(f"Active workspace job: {active_job.title} [{active_job.job_id}]")
    else:
        st.info("No active workspace job selected yet. Open Workspace / Jobs to create or reopen a saved job.")


def _render_admin_logs(runtime: AppRuntime) -> None:
    admin_page.render(runtime, show_admin_controls=True)


def _render_system_logs(runtime: AppRuntime) -> None:
    admin_page.render(runtime, show_admin_controls=False)


def page_labels_for_mode(app_mode: str) -> list[str]:
    mode = app_mode.strip().lower()
    if mode == "admin":
        return [
            "Admin Home",
            "Workspace / Jobs",
            "Tender Analysis",
            "BOQ Pricing",
            "Tender -> Pricing",
            "Manual Ingestion",
            "Admin AI Control",
            "Database Tools",
            "Release Management",
            "Admin / Logs",
        ]
    return [
        "Home / Overview",
        "Workspace / Jobs",
        "Tender Analysis",
        "BOQ Pricing",
        "Tender -> Pricing",
        "System / Logs",
    ]


def build_pages(runtime: AppRuntime) -> dict[str, PageRenderer]:
    if runtime.app_mode == "admin":
        return {
            "Admin Home": lambda: render_admin_home(runtime),
            "Workspace / Jobs": lambda: workspace_page.render(runtime),
            "Tender Analysis": lambda: tender_analysis_page.render(runtime),
            "BOQ Pricing": lambda: boq_pricing_page.render(runtime),
            "Tender -> Pricing": lambda: tender_pricing_page.render(runtime),
            "Manual Ingestion": lambda: manual_ingestion_page.render(runtime),
            "Admin AI Control": lambda: admin_ai_panel.render(runtime),
            "Database Tools": lambda: database_tools_page.render(runtime),
            "Release Management": lambda: render_release_management(runtime),
            "Admin / Logs": lambda: _render_admin_logs(runtime),
        }
    return {
        "Home / Overview": lambda: _render_production_home(runtime),
        "Workspace / Jobs": lambda: workspace_page.render(runtime),
        "Tender Analysis": lambda: tender_analysis_page.render(runtime),
        "BOQ Pricing": lambda: boq_pricing_page.render(runtime),
        "Tender -> Pricing": lambda: tender_pricing_page.render(runtime),
        "System / Logs": lambda: _render_system_logs(runtime),
    }


def run_app(app_mode: str) -> None:
    """Render the selected Streamlit app mode."""

    mode = app_mode.strip().lower()
    page_title = "BOQ AUTO Admin" if mode == "admin" else "BOQ AUTO"
    st.set_page_config(page_title=page_title, layout="wide")
    runtime = build_runtime(app_mode=mode)
    pages = build_pages(runtime)

    st.sidebar.title(page_title)
    selection = st.sidebar.radio("Navigate", list(pages.keys()))
    pages[selection]()
