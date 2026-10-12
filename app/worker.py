"""Local ingestion worker (arq + Redis). Run: arq app.worker.WorkerSettings"""

from arq.connections import RedisSettings

from app.config import get_settings
from app.logging_setup import configure_logging
from app.rag.ingest import ingest_document as run_ingest


async def ingest_document(ctx: dict, document_id: str) -> None:
    await run_ingest(document_id)


async def startup(ctx: dict) -> None:
    configure_logging()


class WorkerSettings:
    functions = [ingest_document]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = 3
    job_timeout = 600
