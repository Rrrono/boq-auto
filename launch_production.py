"""Packaged launcher entrypoint for the BOQ AUTO production app."""

from __future__ import annotations

from src.launcher import launch_streamlit_app


def main() -> None:
    launch_streamlit_app("app.py")


if __name__ == "__main__":
    main()
