"""The /ask flow: redact -> live account lookup -> hybrid retrieval -> grounded answer -> audit."""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_pii
from app.config import get_settings
from app.db.audit import write_audit
from app.domain import ROLE_SCOPES
from app.kyc.policy import build_account_context, guard_restricted_output
from app.kyc.provider import get_kyc_provider
from app.llm import chat_json, embed_texts
from app.logging_setup import request_id_var
from app.rag.prompting import build_messages, parse_answer
from app.rag.retrieve import hybrid_search
from app.security import CurrentUser

NO_CONTEXT_ANSWER = (
    "I couldn't find this in the knowledge base, and no account was specified. "
    "Please check the SOPs directly or escalate to a supervisor."
)


async def answer_question(
    session: AsyncSession, user: CurrentUser, question: str, customer_id: str | None
) -> dict:
    settings = get_settings()
    started = time.perf_counter()
    redacted_question = await get_pii().redact(question)

    account_context, agent_notice, tool_calls = None, None, []
    if customer_id:
        record = await get_kyc_provider().get_status(user.tenant_id, customer_id)
        tool_calls.append({"tool": "kyc_status", "customer_id": customer_id, "found": bool(record)})
        if record:
            account_context, agent_notice = build_account_context(record)

    query_vector = (await embed_texts([redacted_question]))[0]
    chunks = await hybrid_search(
        session,
        tenant_id=user.tenant_id,
        readable_roles=ROLE_SCOPES[user.role],
        query=redacted_question,
        query_vector=query_vector,
        k=settings.retrieval_k,
        top_n=settings.retrieval_top_n,
    )

    usage: dict = {}
    model = None
    if not chunks and account_context is None:
        parsed = {
            "answer": NO_CONTEXT_ANSWER, "citations": [], "suggested_reply": "",
            "needs_escalation": True, "insufficient_context": True,
        }
    else:
        content, usage, model = await chat_json(
            build_messages(redacted_question, chunks, account_context)
        )
        parsed = parse_answer(content, n_chunks=len(chunks))

    guarded_fields: list[str] = []
    if agent_notice:
        parsed["needs_escalation"] = True
        parsed["answer"], parsed["suggested_reply"], guarded_fields = guard_restricted_output(
            parsed["answer"], parsed["suggested_reply"]
        )

    citations = [
        {
            "n": n,
            "chunk_id": chunks[n - 1].id,
            "document_id": chunks[n - 1].document_id,
            "filename": chunks[n - 1].filename,
            "page": chunks[n - 1].page,
            "section": chunks[n - 1].section,
        }
        for n in parsed["citations"]
    ]
    latency_ms = round((time.perf_counter() - started) * 1000)

    await write_audit(
        session,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role,
        action="ask",
        detail={
            "question_redacted": redacted_question,
            "customer_id": customer_id,
            "retrieved_chunk_ids": [c.id for c in chunks],
            "cited_chunk_ids": [c["chunk_id"] for c in citations],
            "tool_calls": tool_calls,
            "restricted_case": agent_notice is not None,
            "guarded_fields": guarded_fields,
            "answer": parsed["answer"],
            "model": model,
            "usage": usage,
            "latency_ms": latency_ms,
        },
    )

    return {
        "request_id": request_id_var.get(),
        "answer": parsed["answer"],
        "suggested_reply": parsed["suggested_reply"],
        "citations": citations,
        "agent_notice": agent_notice,
        "needs_escalation": parsed["needs_escalation"],
        "insufficient_context": parsed["insufficient_context"],
        "model": model,
        "latency_ms": latency_ms,
    }
