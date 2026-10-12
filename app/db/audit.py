from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog
from app.logging_setup import request_id_var


async def write_audit(
    session: AsyncSession, *, tenant_id: str, user_id: str, role: str, action: str, detail: dict
) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            action=action,
            request_id=request_id_var.get(),
            detail=detail,
        )
    )
    await session.commit()
