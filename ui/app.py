"""KYC Copilot web console. Run: streamlit run app.py (from the ui/ directory)."""

import streamlit as st

from components import render_status
from deps import settings
from identity import render_dev_identity_controls

st.set_page_config(page_title="KYC Copilot console", page_icon="🛡️", layout="wide")

try:
    config = settings()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

# Adding a page = one file in pages/ + one line here.
PAGES = [
    st.Page("pages/ask.py", title="Ask", icon="💬", default=True),
    st.Page("pages/scenarios.py", title="Demo scenarios", icon="🎬"),
]
navigation = st.navigation(PAGES)

with st.sidebar:
    render_dev_identity_controls()
    st.divider()
    render_status(config.api_url)

navigation.run()
