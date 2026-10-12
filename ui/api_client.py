"""HTTP client for the KYC Copilot API. The only module in the UI that talks HTTP.

It depends on httpx alone (no Streamlit), so it is easy to test and to reuse.
"""

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

ASK_TIMEOUT_S = 90.0  # SDK + gateway retries can run well past 30 s (TSD T9)
UPLOAD_TIMEOUT_S = 60.0
DEFAULT_TIMEOUT_S = 10.0

# Mirrors the API contract (app/api/ask.py). The API stays authoritative.
QUESTION_MIN, QUESTION_MAX = 3, 2000
CUSTOMER_ID_PATTERN = re.compile(r"^CUS-\d{5}$")


class Caller(Protocol):
    user_id: str
    role: str


class ApiUnavailable(Exception):
    def __init__(self, base_url: str, reason: str) -> None:
        super().__init__(f"API unreachable at {base_url} ({reason})")
        self.base_url = base_url
        self.reason = reason


class ApiError(Exception):
    def __init__(self, status: int, detail: str, request_id: str) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail
        self.request_id = request_id


@dataclass(frozen=True)
class Citation:
    n: int
    chunk_id: str
    document_id: str
    filename: str
    page: int | None
    section: str


@dataclass(frozen=True)
class AskResult:
    request_id: str
    answer: str
    suggested_reply: str
    citations: tuple[Citation, ...]
    agent_notice: str | None
    needs_escalation: bool
    insufficient_context: bool
    model: str | None
    latency_ms: int


@dataclass(frozen=True)
class Document:
    id: str
    filename: str
    status: str
    error: str | None
    source_type: str
    allowed_roles: tuple[str, ...]
    chunk_count: int
    created_at: str


@dataclass(frozen=True)
class UploadResult:
    document: Document
    deduplicated: bool


@dataclass(frozen=True)
class Readiness:
    status: str
    checks: dict[str, str]


def validate_ask_input(question: str, customer_id: str) -> list[str]:
    """Client-side checks that mirror the API, so typos fail fast."""
    errors = []
    if not QUESTION_MIN <= len(question) <= QUESTION_MAX:
        errors.append(f"Question must be {QUESTION_MIN}–{QUESTION_MAX} characters.")
    if customer_id and not CUSTOMER_ID_PATTERN.match(customer_id):
        errors.append("Customer reference must look like CUS-12345 (never an IC number).")
    return errors


class ApiClient:
    def __init__(
        self, base_url: str, identity: Caller, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._identity = identity
        self._transport = transport

    def ask(self, question: str, customer_id: str | None) -> AskResult:
        response = self._request(
            "POST", "/ask", timeout=ASK_TIMEOUT_S,
            json={"question": question, "customer_id": customer_id or None},
        )
        return _ask_result(response.json())

    def list_documents(self) -> list[Document]:
        response = self._request("GET", "/documents", timeout=DEFAULT_TIMEOUT_S)
        return [_document(item) for item in response.json()]

    def upload_document(
        self, filename: str, data: bytes, allowed_roles: Sequence[str], source_type: str
    ) -> UploadResult:
        response = self._request(
            "POST", "/documents", timeout=UPLOAD_TIMEOUT_S, expected=(202,),
            files={"file": (filename, data)},
            data={"allowed_roles": ",".join(allowed_roles), "source_type": source_type},
        )
        body = response.json()
        return UploadResult(document=_document(body), deduplicated=bool(body.get("deduplicated")))

    def reingest(self, document_id: str) -> Document:
        response = self._request(
            "POST", f"/documents/{document_id}/reingest", timeout=DEFAULT_TIMEOUT_S, expected=(202,)
        )
        return _document(response.json())

    def delete_document(self, document_id: str) -> None:
        self._request(
            "DELETE", f"/documents/{document_id}", timeout=DEFAULT_TIMEOUT_S, expected=(204,)
        )

    def readiness(self) -> Readiness:
        # 503 is a normal answer here: it means "degraded", with per-check detail.
        response = self._request("GET", "/readyz", timeout=DEFAULT_TIMEOUT_S, expected=(200, 503))
        body = response.json()
        return Readiness(status=str(body.get("status", "unknown")),
                         checks={str(k): str(v) for k, v in (body.get("checks") or {}).items()})

    def _request(
        self, method: str, path: str, *, timeout: float, expected: tuple[int, ...] = (200,),
        **kwargs: object,
    ) -> httpx.Response:
        request_id = uuid.uuid4().hex
        headers = {
            "X-User-Id": self._identity.user_id,
            "X-User-Role": self._identity.role,
            "X-Request-Id": request_id,
        }
        try:
            with httpx.Client(
                base_url=self._base_url, transport=self._transport, timeout=timeout
            ) as client:
                response = client.request(method, path, headers=headers, **kwargs)
        except httpx.TransportError as exc:  # connection refused, DNS, timeouts
            raise ApiUnavailable(self._base_url, type(exc).__name__) from exc
        if response.status_code not in expected:
            raise _api_error(response, request_id)
        return response


def _api_error(response: httpx.Response, sent_request_id: str) -> ApiError:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    detail = body.get("detail") or response.reason_phrase or "Request failed"
    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(_validation_message(item) for item in detail)
    request_id = next(
        (rid for rid in (body.get("request_id"), response.headers.get("x-request-id"))
         if rid and rid != "-"),  # the API's 500 handler can report "-" (its logs have ours)
        sent_request_id,
    )
    return ApiError(response.status_code, str(detail), str(request_id))


def _validation_message(item: object) -> str:
    if not isinstance(item, dict):
        return str(item)
    location = [str(p) for p in item.get("loc", []) if p not in ("body", "query", "path")]
    message = str(item.get("msg", "invalid value"))
    return f"{'.'.join(location)}: {message}" if location else message


def _document(data: dict) -> Document:
    return Document(
        id=str(data["id"]),
        filename=str(data["filename"]),
        status=str(data["status"]),
        error=data.get("error"),
        source_type=str(data.get("source_type") or ""),
        allowed_roles=tuple(data.get("allowed_roles") or ()),
        chunk_count=int(data.get("chunk_count") or 0),
        created_at=str(data.get("created_at") or ""),
    )


def _ask_result(data: dict) -> AskResult:
    return AskResult(
        request_id=str(data.get("request_id") or ""),
        answer=str(data.get("answer") or ""),
        suggested_reply=str(data.get("suggested_reply") or ""),
        citations=tuple(
            Citation(
                n=int(c["n"]), chunk_id=str(c["chunk_id"]), document_id=str(c["document_id"]),
                filename=str(c["filename"]), page=c.get("page"), section=str(c.get("section") or ""),
            )
            for c in data.get("citations") or ()
        ),
        agent_notice=data.get("agent_notice"),
        needs_escalation=bool(data.get("needs_escalation")),
        insufficient_context=bool(data.get("insufficient_context")),
        model=data.get("model"),
        latency_ms=int(data.get("latency_ms") or 0),
    )
