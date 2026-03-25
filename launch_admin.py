"""Packaged launcher entrypoint for the BOQ AUTO admin app."""

from __future__ import annotations

from src.launcher import launch_streamlit_app


def main() -> None:
    launch_streamlit_app("admin_app.py")


if __name__ == "__main__":
    main()
