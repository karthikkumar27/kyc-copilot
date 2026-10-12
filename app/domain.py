"""Pure domain types shared across layers (no framework imports, so they are easy to test)."""

from dataclasses import dataclass

# Which document access tags each role may read. Retrieval filters on this BEFORE vector
# search, so the model never sees content the user is not allowed to see (OWASP LLM08).
ROLE_SCOPES: dict[str, list[str]] = {
    "agent": ["agent"],
    "supervisor": ["agent", "supervisor"],
    "admin": ["agent", "supervisor", "admin"],
}

TEXT_MIME_TYPES = {"text/plain", "text/markdown"}


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    document_id: str
    filename: str
    page: int | None
    section: str
    content: str
    score: float
