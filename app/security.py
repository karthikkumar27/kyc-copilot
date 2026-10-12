"""Authentication and authorisation.

AUTH_MODE=dev trusts X-User-Id / X-User-Role headers so you can build and test locally.
It is refused when ENVIRONMENT=production (see config.py). Week 4 replaces it with OIDC
(Keycloak locally, Identity Platform / Cognito / Entra ID per cloud) behind the same
CurrentUser dependency, so no endpoint code changes.
"""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings
from app.domain import ROLE_SCOPES


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: str
    tenant_id: str


async def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> CurrentUser:
    settings = get_settings()
    if settings.auth_mode != "dev":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "OIDC auth is planned for week 4")
    role = (x_user_role or "agent").lower()
    if role not in ROLE_SCOPES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Unknown role '{role}'")
    return CurrentUser(user_id=x_user_id or f"dev-{role}", role=role, tenant_id=settings.default_tenant)


def require_role(*allowed: str):
    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return checker
