import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_sessionmaker

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readiness() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {type(exc).__name__}"

    gateway_root = get_settings().llm_base_url.removesuffix("/v1")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{gateway_root}/health/liveliness")
        checks["llm_gateway"] = "ok" if response.status_code == 200 else f"http {response.status_code}"
    except httpx.HTTPError as exc:
        checks["llm_gateway"] = f"error: {type(exc).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse({"status": "ok" if healthy else "degraded", "checks": checks},
                        status_code=200 if healthy else 503)
