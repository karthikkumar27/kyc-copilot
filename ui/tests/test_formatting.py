import pytest

from api_client import Citation
from formatting import citation_line, escape_md, history_title, latency_text, short_id, status_icon
from scenario_data import SCENARIOS, SCENARIOS_BY_ID


@pytest.mark.parametrize("raw", [
    "[click](http://evil.example)",
    "![img](http://evil.example/x.png)",
    "<script>alert(1)</script>",
    "# Heading",
    "**bold** _it_ `code`",
])
def test_escape_md_leaves_no_unescaped_markdown(raw):
    escaped = escape_md(raw)
    for ch in "[]()<>#*_`!":
        assert ch not in escaped.replace("\\" + ch, "")


def test_escape_md_keeps_plain_text_readable():
    assert escape_md("Retry on a dark surface") == "Retry on a dark surface"
    assert escape_md("see [1]") == "see \\[1\\]"


def test_citation_line_with_and_without_page():
    c = Citation(1, "c1", "d1", "SOP-KYC-01.md", None, "Reason code DOC_BLURRY")
    assert citation_line(c) == "[1] SOP-KYC-01.md · Reason code DOC_BLURRY"
    paged = Citation(2, "c2", "d1", "scan.pdf", 3, "")
    assert citation_line(paged) == "[2] scan.pdf · p.3"


@pytest.mark.parametrize("status, icon", [
    ("queued", "⏳"), ("processing", "⚙️"), ("ready", "✅"), ("failed", "❌"), ("weird", "❔"),
])
def test_status_icon(status, icon):
    assert status_icon(status) == icon


def test_small_formatters():
    assert short_id("a1b2c3d4e5f6") == "a1b2c3d4"
    assert latency_text(2140) == "2.1 s"
    long_question = "word " * 30
    title = history_title("agent", "", long_question)
    assert title.startswith("agent · no customer · word") and title.endswith("…")
    assert len(title.split(" · ")[2]) == 60


def test_scenarios_are_well_formed():
    assert len(SCENARIOS) == 7 and len(SCENARIOS_BY_ID) == 7
    for s in SCENARIOS:
        assert s.role in ("agent", "supervisor", "admin")
        assert s.customer_id == "" or s.customer_id.startswith("CUS-")
        assert 3 <= len(s.question) <= 2000 and s.look_for
