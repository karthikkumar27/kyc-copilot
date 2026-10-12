import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("tenant_id", "content_hash", name="uq_documents_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(64))
    storage_uri: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_roles: Mapped[list[str]] = mapped_column(ARRAY(String))
    source_type: Mapped[str] = mapped_column(String(32), default="sop")
    sensitivity: Mapped[str] = mapped_column(String(32), default="internal")
    region: Mapped[str] = mapped_column(String(16), default="MY")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    """Append-only record of who asked what, what was retrieved and what was answered."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
