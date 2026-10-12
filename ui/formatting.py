"""Pure display helpers (no Streamlit import, so they are unit-tested directly).

Model output is never rendered as Markdown: pages show it with st.text. escape_md is for the
remaining places where text we did not write (a question, a filename, a health-check message)
goes into a Markdown-rendering widget such as an expander label.
"""

import re

from api_client import Citation

STATUS_ICONS = {"queued": "⏳", "processing": "⚙️", "ready": "✅", "failed": "❌"}
PENDING_STATUSES = frozenset({"queued", "processing"})

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~:$=])")


def escape_md(text: str) -> str:
    """Backslash-escape Markdown control characters so text renders literally."""
    return _MD_SPECIAL.sub(r"\\\1", text)


def status_icon(status: str) -> str:
    return STATUS_ICONS.get(status, "❔")


def citation_line(citation: Citation) -> str:
    parts = [f"[{citation.n}] {citation.filename}"]
    if citation.section:
        parts.append(citation.section)
    if citation.page is not None:
        parts.append(f"p.{citation.page}")
    return " · ".join(parts)


def short_id(request_id: str) -> str:
    return request_id[:8]


def latency_text(latency_ms: int) -> str:
    return f"{latency_ms / 1000:.1f} s"


def history_title(role: str, customer_id: str, question: str, limit: int = 60) -> str:
    """Plain-text title for a past answer; escape it before using it as a Markdown label."""
    flat = " ".join(question.split())
    if len(flat) > limit:
        flat = flat[: limit - 1] + "…"
    return f"{role} · {customer_id or 'no customer'} · {flat}"
