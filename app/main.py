import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.adapters.factory import validate_adapters
from app.api import ask, documents, health
from app.config import get_settings
from app.db.session import dispose_engine
from app.kyc.provider import get_kyc_provider
from app.logging_setup import configure_logging, request_id_var

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    validate_adapters()
    get_kyc_provider()
    log.info("startup", extra={"extra_fields": {
        "environment": settings.environment,
        "adapters": {
            "storage": settings.storage_provider, "queue": settings.queue_provider,
            "ocr": settings.ocr_provider, "pii": settings.pii_provider,
        },
    }})
    yield
    await dispose_engine()


app = FastAPI(title="KYC Support Copilot", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id  # the 500 handler runs outside this middleware
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Never leak stack traces or provider errors to clients; the request id links to logs.
    request_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    try:
        log.exception("unhandled error")
    finally:
        request_id_var.reset(token)
    return JSONResponse({"detail": "Internal error", "request_id": request_id},
                        status_code=500, headers={"x-request-id": request_id})


app.include_router(health.router)
app.include_router(documents.router)
app.include_router(ask.router)
