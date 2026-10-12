from fakes import FakeClient, ask, ask_result, start

from api_client import ApiError, ApiUnavailable, Readiness

NOTICE = "Restricted case: this verification is under internal review. Use script SCR-REVIEW-01."

def test_answer_sources_and_reply_are_shown():
    client = FakeClient()
    at = ask(start(client), "Why did verification fail?", "CUS-10001")
    assert client.asks == [("Why did verification fail?", "CUS-10001")]
    texts = [t.value for t in at.text]
    assert "Ask the customer to retry on a dark surface [1]." in texts
    assert "[1] SOP-KYC-01.md · Reason code DOC_BLURRY" in texts
    assert at.code[0].value == "Please retry on a dark, flat surface."
    assert not at.error


def test_restricted_notice_is_shown_before_the_answer():
    client = FakeClient(result=ask_result(agent_notice=NOTICE, needs_escalation=True))
    at = ask(start(client), "Was this customer flagged?", "CUS-10004")
    assert "under internal review" in at.error[0].value
    assert any("Escalate" in m.value for m in at.markdown)
    order = [el.type for el in at.main if el.type in ("error", "text")]
    assert order[0] == "error"  # the notice comes before the answer text


def test_model_output_is_not_rendered_as_markdown():
    evil = "[click here](http://evil.example) <b>bold</b>"
    at = ask(start(FakeClient(result=ask_result(answer=evil))), "What now?")
    assert evil in [t.value for t in at.text]
    assert all("evil.example" not in m.value for m in at.markdown)


def test_invalid_customer_reference_is_not_sent():
    client = FakeClient()
    at = ask(start(client), "Why did it fail?", "900101-14-5678")
    assert client.asks == []
    assert "CUS-12345" in at.warning[0].value


def test_api_errors_show_detail_and_request_id():
    client = FakeClient(error=ApiError(422, "customer_id: String should match pattern", "req42"))
    at = ask(start(client), "Why did it fail?")
    assert "HTTP 422" in at.error[0].value and "req42" in at.error[0].value


def test_unreachable_api_is_reported():
    client = FakeClient(error=ApiUnavailable("http://api:8000", "ConnectError"))
    at = ask(start(client), "Why did it fail?")
    assert "API unreachable at http" in at.error[0].value


def test_history_keeps_earlier_answers():
    at = start(FakeClient())
    ask(at, "First question?")
    ask(at, "Second question?")
    assert len(at.expander) == 1 and "First question" in at.expander[0].label


def test_non_ascii_answer_is_shown_intact():
    reply = "Sila cuba semula dan ikut arahan di skrin dengan perlahan-lahan."
    at = ask(start(FakeClient(result=ask_result(answer=reply, suggested_reply=reply))), "Kenapa gagal?")
    assert reply in [t.value for t in at.text] and at.code[0].value == reply


def test_history_is_capped_at_twenty():
    at = start(FakeClient())
    for i in range(22):
        ask(at, f"Question number {i}?")
    assert len(at.session_state["ask_history"]) == 20
    assert len(at.expander) == 19  # the latest is shown in full, the rest collapsed


def test_sidebar_shows_degraded_dependencies():
    degraded = Readiness("degraded", {"database": "ok", "llm_gateway": "error: ConnectError"})
    at = start(FakeClient(readiness=degraded))
    sidebar = [m.value for m in at.sidebar.markdown]
    assert "✅ Database" in sidebar
    assert any(line.startswith("❌ LLM gateway") for line in sidebar)


def test_failed_ask_does_not_show_the_previous_answer_as_current():
    client = FakeClient()
    at = start(client)
    ask(at, "First question?", "CUS-10001")
    client.error = ApiError(500, "Internal error", "req500")
    ask(at, "Second question?", "CUS-10002")
    assert at.error
    assert len(at.expander) == 1 and "First question" in at.expander[0].label


def test_latest_answer_is_labelled_with_its_question():
    at = ask(start(FakeClient()), "Why did verification fail?", "CUS-10001")
    assert any("CUS\-10001" in c.value and "Why did verification fail" in c.value
               for c in at.caption)
