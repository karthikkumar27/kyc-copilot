"""initial schema: documents, chunks (pgvector + full-text), audit_log

Revision ID: 0001
Revises:
"""
from alembic import op

from app.config import get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    dim = get_settings().embedding_dim
    statements = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        """
        CREATE TABLE documents (
            id uuid PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            filename varchar(512) NOT NULL,
            mime_type varchar(128) NOT NULL,
            content_hash varchar(64) NOT NULL,
            storage_uri text NOT NULL,
            status varchar(32) NOT NULL DEFAULT 'queued',
            error text,
            allowed_roles varchar[] NOT NULL,
            source_type varchar(32) NOT NULL DEFAULT 'sop',
            sensitivity varchar(32) NOT NULL DEFAULT 'internal',
            region varchar(16) NOT NULL DEFAULT 'MY',
            chunk_count integer NOT NULL DEFAULT 0,
            created_by varchar(128) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_documents_hash UNIQUE (tenant_id, content_hash)
        )
        """,
        "CREATE INDEX ix_documents_tenant_id ON documents (tenant_id)",
        f"""
        CREATE TABLE chunks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            tenant_id varchar(64) NOT NULL,
            chunk_index integer NOT NULL,
            page integer,
            section text NOT NULL DEFAULT '',
            content text NOT NULL,
            content_tsv tsvector GENERATED ALWAYS AS
                (to_tsvector('simple', section || ' ' || content)) STORED,
            embedding vector({dim}) NOT NULL,
            embedding_model varchar(128) NOT NULL,
            allowed_roles text[] NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_chunks_doc_index UNIQUE (document_id, chunk_index)
        )
        """,
        "CREATE INDEX ix_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)",
        "CREATE INDEX ix_chunks_tsv ON chunks USING gin (content_tsv)",
        "CREATE INDEX ix_chunks_tenant ON chunks (tenant_id)",
        "CREATE INDEX ix_chunks_roles ON chunks USING gin (allowed_roles)",
        """
        CREATE TABLE audit_log (
            id uuid PRIMARY KEY,
            ts timestamptz NOT NULL DEFAULT now(),
            tenant_id varchar(64) NOT NULL,
            user_id varchar(128) NOT NULL,
            role varchar(32) NOT NULL,
            action varchar(64) NOT NULL,
            request_id varchar(64) NOT NULL,
            detail jsonb NOT NULL DEFAULT '{}'::jsonb
        )
        """,
        "CREATE INDEX ix_audit_log_tenant_id ON audit_log (tenant_id)",
        "CREATE INDEX ix_audit_log_ts ON audit_log (ts)",
        # Append-only: the application role may insert and read audit rows, never change them.
        """
        CREATE FUNCTION audit_log_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'audit_log is append-only'; END; $$
        """,
        """
        CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable()
        """,
    ]
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    for statement in [
        "DROP TABLE IF EXISTS audit_log",
        "DROP FUNCTION IF EXISTS audit_log_immutable()",
        "DROP TABLE IF EXISTS chunks",
        "DROP TABLE IF EXISTS documents",
    ]:
        op.execute(statement)
