from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent


def test_no_legacy_pages_directory():
    # Streamlit auto-discovers ui/pages/: a first-visit deep link such as /documents then runs
    # the page on its own, without app.py's sidebar, identity and status.
    assert not (UI_DIR / "pages").exists()
