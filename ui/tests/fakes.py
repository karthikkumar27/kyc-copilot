"""Test helpers: a stand-in for ApiClient that records calls, and AppTest shortcuts."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from api_client import AskResult, Citation, Document, Readiness, UploadResult
from deps import CLIENT_OVERRIDE_KEY

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def ask_result(**overrides) -> AskResult:
    values = dict(
        request_id="a1b2c3d4e5f6", answer="Ask the customer to retry on a dark surface [1].",
        suggested_reply="Please retry on a dark, flat surface.",
        citations=(Citation(1, "c1", "d1", "SOP-KYC-01.md", None, "Reason code DOC_BLURRY"),),
        agent_notice=None, needs_escalation=False, insufficient_context=False,
        model="gemini-2.5-flash", latency_ms=2140,
    )
    values.update(overrides)
    return AskResult(**values)


def document(**overrides) -> Document:
    values = dict(id="d1", filename="SOP-KYC-01.md", status="ready", error=None,
                  source_type="sop", allowed_roles=("agent", "supervisor", "admin"),
                  chunk_count=9, created_at="2026-10-12T10:00:00Z")
    values.update(overrides)
    return Document(**values)


class FakeClient:
    def __init__(self, *, result=None, documents=(), readiness=None, error=None,
                 action_error=None):
        self.result = result or ask_result()
        self.documents = list(documents)
        self.readiness_result = readiness or Readiness("ok", {"database": "ok", "llm_gateway": "ok"})
        self.error = error
        self.action_error = action_error  # raised by reingest/delete
        self.asks: list[tuple[str, str | None]] = []
        self.uploads: list[tuple] = []

    def ask(self, question, customer_id):
        self.asks.append((question, customer_id))
        if self.error:
            raise self.error
        return self.result

    def list_documents(self):
        if self.error:
            raise self.error
        return list(self.documents)

    def readiness(self):
        return self.readiness_result

    def upload_document(self, filename, data, allowed_roles, source_type):
        self.uploads.append((filename, data, tuple(allowed_roles), source_type))
        return UploadResult(document(filename=filename, status="queued"), deduplicated=False)

    def reingest(self, document_id):
        if self.action_error:
            raise self.action_error
        return document(id=document_id, status="queued")

    def delete_document(self, document_id):
        if self.action_error:
            raise self.action_error
        return None


def start(client: FakeClient, role: str = "agent", page: str | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=10)
    at.session_state[CLIENT_OVERRIDE_KEY] = client
    at.session_state["role"] = role
    at.run()
    if page:
        at.switch_page(page).run()
    return at


def ask(at: AppTest, question: str, customer: str = "") -> AppTest:
    at.text_area(key="ask_question").input(question)
    at.text_input(key="ask_customer").input(customer)
    return at.button[0].click().run()  # the form's submit button
