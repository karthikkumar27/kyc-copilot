"""Ingestion pipeline: storage -> OCR -> PII redaction -> chunk -> embed -> index.

Idempotent: re-running for the same document replaces its chunks in one transaction, so a
retried job never leaves duplicates. Called by the arq worker (local) and by the Cloud Tasks
HTTP worker (GCP).
"""

import logging
import time
import uuid

from sqlalchemy import select, text, update

from app.adapters.factory import get_ocr, get_pii, get_storage
from app.config import get_settings
from app.db.models import Document
from app.db.session import get_sessionmaker
from app.domain import TEXT_MIME_TYPES, PageText
from app.llm import embed_texts, to_pgvector
from app.rag.chunking import chunk_pages

log = logging.getLogger(__name__)

INSERT_CHUNK = text(
    """
    INSERT INTO chunks (document_id, tenant_id, chunk_index, page, section, content,
                        embedding, embedding_model, allowed_roles)
    VALUES (:document_id, :tenant_id, :chunk_index, :page, :section, :content,
            CAST(CAST(:embedding AS text) AS vector), :embedding_model,
            CAST(:allowed_roles AS text[]))
    """
)


async def ingest_document(document_id: str) -> None:
    settings = get_settings()
    doc_id = uuid.UUID(document_id)
    started = time.perf_counter()

    async with get_sessionmaker()() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
        if doc is None:
            log.warning("ingest: document not found", extra={"extra_fields": {"document_id": document_id}})
            return
        if doc.status == "ready":
            return
        tenant_id, mime, uri, roles = doc.tenant_id, doc.mime_type, doc.storage_uri, list(doc.allowed_roles)
        await session.execute(
            update(Document).where(Document.id == doc_id).values(status="processing", error=None)
        )
        await session.commit()

        try:
            data = await get_storage().get(uri)
            if mime in TEXT_MIME_TYPES:
                pages = [PageText(1, data.decode("utf-8", errors="replace"))]
            else:
                pages = await get_ocr().extract(data, mime)

            redactor = get_pii()
            pages = [PageText(p.page, await redactor.redact(p.text)) for p in pages]

            chunks = chunk_pages(pages, settings.chunk_max_chars, settings.chunk_overlap_chars)
            if not chunks:
                raise ValueError("No text could be extracted from the document")

            vectors = await embed_texts([c.embedding_text() for c in chunks])
            rows = [
                {
                    "document_id": doc_id,
                    "tenant_id": tenant_id,
                    "chunk_index": c.index,
                    "page": c.page,
                    "section": c.section,
                    "content": c.text,
                    "embedding": to_pgvector(v),
                    "embedding_model": settings.embed_model,
                    "allowed_roles": roles,
                }
                for c, v in zip(chunks, vectors, strict=True)
            ]
            await session.execute(text("DELETE FROM chunks WHERE document_id = :d"), {"d": doc_id})
            await session.execute(INSERT_CHUNK, rows)
            await session.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="ready", chunk_count=len(rows), error=None)
            )
            await session.commit()
            log.info(
                "ingest: done",
                extra={"extra_fields": {
                    "document_id": document_id, "chunks": len(rows),
                    "ms": round((time.perf_counter() - started) * 1000),
                }},
            )
        except Exception as exc:
            await session.rollback()
            await session.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="failed", error=f"{type(exc).__name__}: {exc}"[:2000])
            )
            await session.commit()
            log.exception("ingest: failed", extra={"extra_fields": {"document_id": document_id}})
            raise
