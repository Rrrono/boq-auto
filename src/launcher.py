"""Windows-friendly launch helpers for packaged Streamlit entrypoints."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def streamlit_argv(script_name: str, server_headless: bool = False) -> list[str]:
    """Build deterministic argv for launching a bundled Streamlit app."""

    script_path = _repo_root() / script_name
    return [
        "streamlit",
        "run",
        str(script_path),
        "--server.headless",
        "true" if server_headless else "false",
        "--browser.gatherUsageStats",
        "false",
    ]


def launch_streamlit_app(script_name: str, server_headless: bool = False) -> None:
    """Launch a Streamlit app through its CLI so packaged EXEs behave correctly."""

    argv = streamlit_argv(script_name, server_headless=server_headless)
    sys.argv = argv
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    try:
        from streamlit.web.cli import main as streamlit_main
    except Exception as exc:
        raise RuntimeError("Streamlit is not installed or could not be imported.") from exc
    raise SystemExit(streamlit_main())
