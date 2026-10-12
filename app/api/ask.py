from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.rag.answer import answer_question
from app.security import CurrentUser, get_current_user

router = APIRouter(tags=["copilot"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    customer_id: str | None = Field(default=None, pattern=r"^CUS-\d{5}$",
                                    description="Internal customer reference, never an IC number")


class Citation(BaseModel):
    n: int
    chunk_id: str
    document_id: str
    filename: str
    page: int | None
    section: str


class AskResponse(BaseModel):
    request_id: str
    answer: str
    suggested_reply: str
    citations: list[Citation]
    agent_notice: str | None
    needs_escalation: bool
    insufficient_context: bool
    model: str | None
    latency_ms: int


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await answer_question(session, user, body.question, body.customer_id)
