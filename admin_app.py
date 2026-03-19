"""Private owner/admin Streamlit app for BOQ AUTO."""

from __future__ import annotations

from ui.app_shell import run_app


def main() -> None:
    run_app("admin")


if __name__ == "__main__":
    main()
