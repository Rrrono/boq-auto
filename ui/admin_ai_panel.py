"""Admin-only AI control panel."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ai.admin_tools import generate_embeddings, get_embedding_stats, reset_embeddings, test_ai_connection
from src.audit_logger import log_event
from src.config_loader import load_config, save_local_config
from src.cost_schema import CostDatabase, schema_database_path
from src.release_manager import master_database_path
from ui.helpers import get_current_mode_label, safe_error_message


def _operator_name() -> str:
    return str(st.session_state.get("operator_name", "")).strip() or "Admin"


def _config_snapshot(config) -> dict:
    return {
        "ai": dict(config.data.get("ai", {})),
        "matching": {"mode": config.get("matching.mode", "rule")},
    }


def _log(operator_name: str, action: str, config, details: dict | None = None) -> None:
    payload = {
        "config_snapshot": _config_snapshot(config),
    }
    if details:
        payload.update(details)
    log_event(operator_name, action, payload)


def render(runtime) -> None:
    """Render the admin AI control panel."""

    if runtime.app_mode != "admin":
        st.info("AI controls are available only in the admin app.")
        return

    st.header("Admin AI Control Panel")
    st.write("Manage optional AI behavior safely for admin workflows. Production pricing remains protected by release snapshots and fallback-to-rule behavior.")

    operator_name = _operator_name()
    config = load_config()
    master_db = Path(master_database_path(config))
    schema_path = schema_database_path(master_db)
    repository = CostDatabase(schema_path)

    st.caption(f"Current operator: {operator_name}")
    st.caption(f"Master database: {master_db}")
    st.caption(f"Schema database: {schema_path}")
    st.caption(f"Current mode: {get_current_mode_label(config, str(config.get('matching.mode', 'rule')))}")

    with st.expander("AI Configuration", expanded=True):
        enabled = st.checkbox("Enable AI", value=bool(config.get("ai.enabled", False)), key="admin_ai_enabled")
        matching_mode = st.selectbox(
            "Matching Mode",
            options=["rule", "hybrid", "ai"],
            index=["rule", "hybrid", "ai"].index(str(config.get("matching.mode", "rule")).strip().lower() or "rule"),
            key="admin_ai_matching_mode",
        )
        model_name = st.text_input(
            "Model name",
            value=str(config.get("ai.model", config.get("ai.embedding_model", "text-embedding-3-small"))),
            key="admin_ai_model_name",
        )
        st.caption("API keys are never stored here. Set OPENAI_API_KEY in the environment on the admin machine.")
        if enabled and not os.getenv("OPENAI_API_KEY", "").strip():
            st.warning("OPENAI_API_KEY is not set. The system will fall back safely until a key is available.")
        if st.button("Save Settings", type="primary", key="admin_ai_save_settings"):
            try:
                save_local_config(
                    {
                        "ai": {
                            "enabled": bool(enabled),
                            "provider": "openai",
                            "model": model_name.strip() or "text-embedding-3-small",
                            "embedding_model": model_name.strip() or "text-embedding-3-small",
                            "use_env_key": True,
                        },
                        "matching": {
                            "mode": matching_mode,
                        },
                    }
                )
                updated = load_config()
                _log(operator_name, "ai_settings_updated", updated, {"saved_to": "config/local.yaml"})
                st.success("AI settings saved to config/local.yaml.")
                st.caption(f"Matching Mode: {get_current_mode_label(updated, str(updated.get('matching.mode', 'rule')))}")
            except Exception as exc:
                st.error(safe_error_message(exc))

        if st.button("Test AI Connection", key="admin_ai_test_connection"):
            try:
                success, message, provider = test_ai_connection(config)
                _log(
                    operator_name,
                    "ai_test_run",
                    config,
                    {
                        "success": success,
                        "provider": getattr(provider, "model_name", "") if provider is not None else "",
                    },
                )
                if success:
                    st.success(f"AI connection successful. {message}")
                else:
                    st.warning(f"AI unavailable - fallback will be used. {message}")
            except Exception as exc:
                _log(operator_name, "ai_test_run", config, {"success": False, "error": str(exc)})
                st.warning("AI unavailable - fallback will be used.")
                st.caption(safe_error_message(exc))

    with st.expander("Embeddings Management", expanded=True):
        stats = get_embedding_stats(repository)
        stats_cols = st.columns(3)
        stats_cols[0].metric("Total items", int(stats.get("total_items", 0)))
        stats_cols[1].metric("Embedded items", int(stats.get("embedded_items", 0)))
        stats_cols[2].metric("Last updated", str(stats.get("last_updated", "") or "Not yet"))

        if not bool(config.get("ai.enabled", False)):
            st.info("AI is disabled. Embedding generation is available only when AI is enabled.")

        action_cols = st.columns(2)
        if action_cols[0].button(
            "Generate Embeddings",
            key="admin_ai_generate_embeddings",
            disabled=not bool(config.get("ai.enabled", False)),
        ):
            try:
                success, message, provider = test_ai_connection(config)
                if not success or provider is None:
                    _log(operator_name, "embeddings_generated", config, {"generated": 0, "skipped": True, "reason": message})
                    st.warning(message)
                else:
                    generated = generate_embeddings(repository, provider)
                    _log(operator_name, "embeddings_generated", config, {"generated": generated, "model": getattr(provider, "model_name", "")})
                    st.success(f"Generated embeddings for {generated} item(s).")
            except Exception as exc:
                _log(operator_name, "embeddings_generated", config, {"generated": 0, "error": str(exc)})
                st.error(safe_error_message(exc))

        if action_cols[1].button("Reset Embeddings", key="admin_ai_reset_embeddings"):
            try:
                removed = reset_embeddings(repository)
                _log(operator_name, "embeddings_reset", config, {"removed": removed})
                st.success(f"Reset embeddings. Removed {removed} stored record(s).")
            except Exception as exc:
                _log(operator_name, "embeddings_reset", config, {"removed": 0, "error": str(exc)})
                st.error(safe_error_message(exc))

        st.caption(f"Matching Mode: {get_current_mode_label(config, str(config.get('matching.mode', 'rule')))}")

        with st.expander("Embedding Stats", expanded=False):
            st.json(stats)

        with st.expander("Inspect Embeddings", expanded=False):
            records = repository.fetch_embedding_records(limit=25)
            if not records:
                st.caption("No embeddings stored yet.")
            else:
                st.dataframe(pd.DataFrame(records), use_container_width=True)
