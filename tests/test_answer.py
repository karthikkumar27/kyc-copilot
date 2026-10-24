"""answer_question orchestration with every dependency mocked (INV-05 payload, restricted guard)."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.kyc.policy import RESTRICTED_AGENT_NOTICE
from app.rag import answer as mod

USER = SimpleNamespace(tenant_id="t1", user_id="u1", role="agent")
RESTRICTED = {"customer_id": "CUS-10004", "verification_status": "REJECTED",
              "reason_code": "SANCTIONS_SCREENING_HIT"}
CHUNK = SimpleNamespace(id="c1", document_id="d1", filename="SOP-ESC-03.md", page=1, section="s",
                        content="Escalate restricted cases.")


def run(monkeypatch, record, model_json):
    chat, audit = AsyncMock(return_value=(json.dumps(model_json), {}, "m")), AsyncMock()
    monkeypatch.setattr(mod, "get_pii", lambda: SimpleNamespace(redact=AsyncMock(side_effect=lambda q: q)))
    monkeypatch.setattr(mod, "get_kyc_provider",
                        lambda: SimpleNamespace(get_status=AsyncMock(return_value=record)))
    monkeypatch.setattr(mod, "embed_texts", AsyncMock(return_value=[[0.0]]))
    monkeypatch.setattr(mod, "hybrid_search", AsyncMock(return_value=[CHUNK]))
    monkeypatch.setattr(mod, "chat_json", chat)
    monkeypatch.setattr(mod, "write_audit", audit)
    result = asyncio.run(mod.answer_question(None, USER, "Was CUS-10004 sanctioned?", "CUS-10004"))
    return result, chat, audit


def model_says(answer, reply):
    return {"answer": answer, "citations": [1], "suggested_reply": reply,
            "needs_escalation": False, "insufficient_context": False}


def test_restricted_output_is_guarded_and_audited(monkeypatch):
    result, _, audit = run(monkeypatch, RESTRICTED, model_says("It is a sanctions hit [1].", "ok"))
    assert result["answer"] == RESTRICTED_AGENT_NOTICE
    assert result["suggested_reply"] == "ok"
    assert result["needs_escalation"] is True
    assert result["citations"][0]["filename"] == "SOP-ESC-03.md"
    detail = audit.call_args.kwargs["detail"]
    assert detail["answer"] == RESTRICTED_AGENT_NOTICE and detail["guarded_fields"] == ["answer"]


def test_clean_restricted_output_is_untouched(monkeypatch):
    result, _, audit = run(monkeypatch, RESTRICTED, model_says("Escalate per SOP-ESC-03 [1].", "r"))
    assert result["answer"] == "Escalate per SOP-ESC-03 [1]."
    assert audit.call_args.kwargs["detail"]["guarded_fields"] == []


def test_guard_does_not_run_for_unrestricted_cases(monkeypatch):
    record = {"customer_id": "CUS-10001", "verification_status": "REJECTED",
              "reason_code": "DOC_BLURRY"}
    result, _, audit = run(monkeypatch, record, model_says("Fraud checks never apply here.", "r"))
    assert "Fraud" in result["answer"]
    assert audit.call_args.kwargs["detail"]["guarded_fields"] == []


def test_gateway_payload_never_contains_the_internal_reason(monkeypatch):
    _, chat, _ = run(monkeypatch, RESTRICTED, model_says("Escalate [1].", "r"))
    payload = json.dumps(chat.call_args.args[0])
    assert "SANCTIONS_SCREENING_HIT" not in payload and "reason_code" not in payload
    assert "SCR-REVIEW-01" in payload


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(mod, "get_settings",
                        lambda: SimpleNamespace(retrieval_k=20, retrieval_top_n=6))
