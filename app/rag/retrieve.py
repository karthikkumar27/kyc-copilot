"""Hybrid retrieval: pgvector (semantic) + Postgres full-text (exact terms such as reason
codes and SOP IDs), fused with Reciprocal Rank Fusion.

Access control is applied inside both searches, before ranking, so restricted chunks never
reach the model. The 'simple' text-search config is used because content mixes English and
Bahasa Melayu.

Note: with restrictive filters an HNSW scan can return fewer than k rows. pgvector >= 0.8
supports `SET hnsw.iterative_scan = relaxed_order` to fix this; enable it once your managed
Postgres ships that version.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import RetrievedChunk
from app.llm import to_pgvector

RRF_K = 60

HYBRID_SQL = text(
    """
    WITH q AS (
        SELECT CAST(CAST(:qvec AS text) AS vector) AS v,
               websearch_to_tsquery('simple', :query) AS ts
    ),
    vec AS (
        SELECT id, row_number() OVER (ORDER BY dist) AS r FROM (
            SELECT c.id, c.embedding <=> q.v AS dist
            FROM chunks c, q
            WHERE c.tenant_id = :tenant AND c.allowed_roles && CAST(:roles AS text[])
            ORDER BY c.embedding <=> q.v
            LIMIT :k
        ) s
    ),
    kw AS (
        SELECT id, row_number() OVER (ORDER BY rank DESC) AS r FROM (
            SELECT c.id, ts_rank_cd(c.content_tsv, q.ts) AS rank
            FROM chunks c, q
            WHERE c.tenant_id = :tenant AND c.allowed_roles && CAST(:roles AS text[])
              AND c.content_tsv @@ q.ts
            ORDER BY rank DESC
            LIMIT :k
        ) s
    )
    SELECT c.id, c.document_id, d.filename, c.page, c.section, c.content,
           COALESCE(1.0 / (:rrf_k + vec.r), 0) + COALESCE(1.0 / (:rrf_k + kw.r), 0) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    LEFT JOIN vec ON vec.id = c.id
    LEFT JOIN kw ON kw.id = c.id
    WHERE vec.id IS NOT NULL OR kw.id IS NOT NULL
    ORDER BY score DESC
    LIMIT :top_n
    """
)


async def hybrid_search(
    session: AsyncSession,
    *,
    tenant_id: str,
    readable_roles: list[str],
    query: str,
    query_vector: list[float],
    k: int,
    top_n: int,
) -> list[RetrievedChunk]:
    result = await session.execute(
        HYBRID_SQL,
        {
            "qvec": to_pgvector(query_vector),
            "query": query,
            "tenant": tenant_id,
            "roles": readable_roles,
            "k": k,
            "top_n": top_n,
            "rrf_k": RRF_K,
        },
    )
    return [
        RetrievedChunk(
            id=str(row.id),
            document_id=str(row.document_id),
            filename=row.filename,
            page=row.page,
            section=row.section or "",
            content=row.content,
            score=float(row.score),
        )
        for row in result
    ]
