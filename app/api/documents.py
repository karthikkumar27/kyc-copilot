import hashlib
import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_queue, get_storage
from app.config import get_settings
from app.db.audit import write_audit
from app.db.models import Document
from app.db.session import get_session
from app.domain import ROLE_SCOPES
from app.security import CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/documents", tags=["documents"])
log = logging.getLogger(__name__)

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".md": "text/markdown",
    ".txt": "text/plain",
}
SOURCE_TYPES = {"sop", "regulation", "faq", "script"}


def _serialize(doc: Document) -> dict:
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "error": doc.error,
        "source_type": doc.source_type,
        "allowed_roles": doc.allowed_roles,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at,
    }


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    allowed_roles: str = Form("agent,supervisor,admin"),
    source_type: str = Form("sop"),
    user: CurrentUser = Depends(require_role("supervisor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    filename = file.filename or "upload"
    mime = ALLOWED_TYPES.get(Path(filename).suffix.lower())
    if mime is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Allowed: {sorted(ALLOWED_TYPES)}")
    if source_type not in SOURCE_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"source_type must be one of {sorted(SOURCE_TYPES)}")
    roles = sorted({r.strip().lower() for r in allowed_roles.split(",") if r.strip()})
    if not roles or not set(roles) <= set(ROLE_SCOPES):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Roles must be from {sorted(ROLE_SCOPES)}")

    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Max {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    content_hash = hashlib.sha256(data).hexdigest()
    existing = await session.scalar(
        select(Document).where(Document.tenant_id == user.tenant_id, Document.content_hash == content_hash)
    )
    if existing:
        return {**_serialize(existing), "deduplicated": True}

    doc_id = uuid.uuid4()
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:120]
    uri = await get_storage().put(f"{user.tenant_id}/{doc_id}/{safe_name}", data, mime)
    doc = Document(
        id=doc_id, tenant_id=user.tenant_id, filename=filename, mime_type=mime,
        content_hash=content_hash, storage_uri=uri, status="queued", allowed_roles=roles,
        source_type=source_type, created_by=user.user_id,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)  # load server defaults (created_at) without lazy IO later
    await get_queue().enqueue_ingest(str(doc_id))
    await write_audit(session, tenant_id=user.tenant_id, user_id=user.user_id, role=user.role,
                      action="document.upload", detail={"document_id": str(doc_id), "filename": filename})
    return {**_serialize(doc), "deduplicated": False}


@router.get("")
async def list_documents(
    user: CurrentUser = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = await session.scalars(
        select(Document)
        .where(Document.tenant_id == user.tenant_id,
               Document.allowed_roles.overlap(ROLE_SCOPES[user.role]))
        .order_by(Document.created_at.desc())
    )
    return [_serialize(d) for d in rows]


async def _get_owned(session: AsyncSession, user: CurrentUser, document_id: uuid.UUID) -> Document:
    doc = await session.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == user.tenant_id)
    )
    if doc is None or not set(doc.allowed_roles) & set(ROLE_SCOPES[user.role]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return _serialize(await _get_owned(session, user, document_id))


@router.post("/{document_id}/reingest", status_code=status.HTTP_202_ACCEPTED)
async def reingest_document(
    document_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("supervisor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    doc = await _get_owned(session, user, document_id)
    doc.status = "queued"
    await session.commit()
    await get_queue().enqueue_ingest(str(doc.id))
    return _serialize(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Deletion propagates: chunks and embeddings go via ON DELETE CASCADE, then the file."""
    doc = await _get_owned(session, user, document_id)
    uri, filename = doc.storage_uri, doc.filename
    await session.execute(delete(Document).where(Document.id == doc.id))
    await session.commit()
    try:
        await get_storage().delete(uri)
    except Exception:  # noqa: BLE001
        log.exception("delete: stored file could not be removed; schedule cleanup",
                      extra={"extra_fields": {"uri": uri}})
    await write_audit(session, tenant_id=user.tenant_id, user_id=user.user_id, role=user.role,
                      action="document.delete", detail={"document_id": str(document_id), "filename": filename})
