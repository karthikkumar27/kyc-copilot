"""Rendering helpers shared by pages and the sidebar."""

import streamlit as st

from api_client import ApiError, ApiUnavailable
from deps import readiness
from formatting import escape_md

CHECK_LABELS = (("database", "Database"), ("llm_gateway", "LLM gateway"))


def show_error(exc: ApiError | ApiUnavailable) -> None:
    if isinstance(exc, ApiUnavailable):
        st.error(escape_md(str(exc)))
    elif exc.status >= 500:
        st.error(f"Internal error (request {escape_md(exc.request_id)})")
    else:
        st.error(f"{escape_md(exc.detail)} (HTTP {exc.status}, request {escape_md(exc.request_id)})")


def render_status(api_url: str) -> None:
    st.subheader("Status")
    try:
        result = readiness()
    except ApiUnavailable:
        st.markdown("❌ API unreachable")
    except ApiError as exc:
        st.markdown(f"❌ API error (HTTP {exc.status})")
    else:
        st.markdown("✅ API")
        for key, label in CHECK_LABELS:
            value = result.checks.get(key, "unknown")
            line = f"✅ {label}" if value == "ok" else f"❌ {label}: {escape_md(value)}"
            st.markdown(line)
    st.caption(escape_md(api_url))
