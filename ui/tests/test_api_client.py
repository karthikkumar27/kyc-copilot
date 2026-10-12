import json

import httpx
import pytest

from api_client import (
    ASK_TIMEOUT_S,
    DEFAULT_TIMEOUT_S,
    UPLOAD_TIMEOUT_S,
    ApiClient,
    ApiError,
    ApiUnavailable,
    validate_ask_input,
)


class Who:
    user_id = "ui-supervisor"
    role = "supervisor"


DOC = {"id": "d1", "filename": "SOP.md", "status": "ready", "error": None, "source_type": "sop",
       "allowed_roles": ["agent", "supervisor"], "chunk_count": 4,
       "created_at": "2026-10-12T10:00:00Z", "some_future_field": 1}

ASK = {"request_id": "r1", "answer": "Retry on a dark surface [1].", "suggested_reply": "Hi",
       "citations": [{"n": 1, "chunk_id": "c1", "document_id": "d1", "filename": "SOP.md",
                      "page": None, "section": "DOC_BLURRY"}],
       "agent_notice": None, "needs_escalation": False, "insufficient_context": False,
       "model": "gemini-2.5-flash", "latency_ms": 2140, "unknown": "ignored"}


def make_client(handler):
    return ApiClient("http://api:8000/", Who(), transport=httpx.MockTransport(handler))


def test_every_call_sends_identity_and_a_fresh_request_id():
    seen = []

    def handler(request):
        seen.append(request.headers)
        return httpx.Response(200, json=[])

    client = make_client(handler)
    client.list_documents()
    client.list_documents()
    assert seen[0]["x-user-id"] == "ui-supervisor" and seen[0]["x-user-role"] == "supervisor"
    assert len(seen[0]["x-request-id"]) == 32
    assert seen[0]["x-request-id"] != seen[1]["x-request-id"]


@pytest.mark.parametrize("call, status, body, expected_timeout", [
    (lambda c: c.ask("What is the limit?", None), 200, ASK, ASK_TIMEOUT_S),
    (lambda c: c.upload_document("a.md", b"x", ["agent"], "sop"), 202, DOC, UPLOAD_TIMEOUT_S),
    (lambda c: c.list_documents(), 200, [], DEFAULT_TIMEOUT_S),
    (lambda c: c.readiness(), 200, {"status": "ok", "checks": {}}, DEFAULT_TIMEOUT_S),
])
def test_each_method_uses_its_timeout(call, status, body, expected_timeout):
    timeouts = []

    def handler(request):
        timeouts.append(request.extensions["timeout"]["read"])
        return httpx.Response(status, json=body)

    call(make_client(handler))
    assert timeouts == [expected_timeout]


def test_ask_maps_json_and_ignores_unknown_fields():
    def handler(request):
        assert request.method == "POST" and request.url.path == "/ask"
        assert json.loads(request.content) == {"question": "Why?", "customer_id": None}
        return httpx.Response(200, json=ASK)

    result = make_client(handler).ask("Why?", "")
    assert result.answer.startswith("Retry") and result.latency_ms == 2140
    assert result.citations[0].section == "DOC_BLURRY" and result.citations[0].page is None


def test_upload_sends_multipart_fields_and_reports_dedup():
    def handler(request):
        body = request.content.decode()
        assert request.url.path == "/documents"
        assert 'name="file"; filename="SOP.md"' in body
        assert 'name="allowed_roles"' in body and "agent,supervisor" in body
        assert 'name="source_type"' in body and "faq" in body
        return httpx.Response(202, json={**DOC, "deduplicated": True})

    result = make_client(handler).upload_document("SOP.md", b"# SOP", ["agent", "supervisor"], "faq")
    assert result.deduplicated is True
    assert result.document.allowed_roles == ("agent", "supervisor")


def test_reingest_and_delete_hit_the_right_routes():
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(202, json={**DOC, "status": "queued"})

    client = make_client(handler)
    assert client.reingest("d1").status == "queued"
    client.delete_document("d1")
    assert calls == [("POST", "/documents/d1/reingest"), ("DELETE", "/documents/d1")]


def test_readiness_treats_503_as_degraded_not_error():
    def handler(request):
        return httpx.Response(503, json={"status": "degraded",
                                         "checks": {"database": "ok", "llm_gateway": "http 500"}})

    readiness = make_client(handler).readiness()
    assert readiness.status == "degraded" and readiness.checks["llm_gateway"] == "http 500"


def test_http_error_carries_detail_and_request_id_from_body():
    def handler(request):
        return httpx.Response(403, json={"detail": "Insufficient role"},
                              headers={"x-request-id": "from-header"})

    with pytest.raises(ApiError) as info:
        make_client(handler).delete_document("d1")
    assert info.value.status == 403 and info.value.detail == "Insufficient role"
    assert info.value.request_id == "from-header"


def test_server_error_prefers_request_id_in_body():
    def handler(request):
        return httpx.Response(500, json={"detail": "Internal error", "request_id": "from-body"},
                              headers={"x-request-id": "from-header"})

    with pytest.raises(ApiError) as info:
        make_client(handler).list_documents()
    assert info.value.request_id == "from-body"


def test_validation_errors_are_flattened():
    def handler(request):
        return httpx.Response(422, json={"detail": [
            {"loc": ["body", "customer_id"], "msg": "String should match pattern"}]})

    with pytest.raises(ApiError) as info:
        make_client(handler).ask("Why?", "CUS-1")
    assert info.value.detail == "customer_id: String should match pattern"


def test_non_json_error_falls_back_to_reason_and_sent_request_id():
    sent = []

    def handler(request):
        sent.append(request.headers["x-request-id"])
        return httpx.Response(502, text="<html>bad gateway</html>")

    with pytest.raises(ApiError) as info:
        make_client(handler).list_documents()
    assert info.value.detail == "Bad Gateway" and info.value.request_id == sent[0]


@pytest.mark.parametrize("exc", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
def test_transport_failures_become_unavailable(exc):
    def handler(request):
        raise exc

    with pytest.raises(ApiUnavailable, match="API unreachable at http://api:8000"):
        make_client(handler).list_documents()


@pytest.mark.parametrize("question, customer, errors", [
    ("Why did it fail?", "", 0),
    ("Why did it fail?", "CUS-10001", 0),
    ("Hi", "", 1),
    ("x" * 2001, "", 1),
    ("Why did it fail?", "900101-14-5678", 1),  # an IC number is never accepted
    ("Why did it fail?", "cus-10001", 1),
])
def test_validate_ask_input(question, customer, errors):
    assert len(validate_ask_input(question, customer)) == errors


def test_placeholder_request_id_falls_back_to_the_one_sent():
    # The API's 500 handler can report "-"; its logs carry the ID the client sent.
    sent = []

    def handler(request):
        sent.append(request.headers["x-request-id"])
        return httpx.Response(500, json={"detail": "Internal error", "request_id": "-"})

    with pytest.raises(ApiError) as info:
        make_client(handler).list_documents()
    assert info.value.request_id == sent[0]
