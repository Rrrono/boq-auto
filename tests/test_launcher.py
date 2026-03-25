from src.launcher import streamlit_argv


def test_streamlit_argv_targets_expected_script() -> None:
    argv = streamlit_argv("app.py")

    assert argv[0:2] == ["streamlit", "run"]
    assert argv[2].endswith("app.py")
    assert "--server.headless" in argv
    assert "--browser.gatherUsageStats" in argv
