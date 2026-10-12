"""Local queue: Redis + arq. The worker runs app.worker.WorkerSettings."""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings


class ArqQueue:
    def __init__(self, settings) -> None:
        self._redis_settings = RedisSettings.from_dsn(settings.redis_url)
        self._pool: ArqRedis | None = None

    async def enqueue_ingest(self, document_id: str) -> None:
        if self._pool is None:
            self._pool = await create_pool(self._redis_settings)
        # _job_id makes enqueueing idempotent while a job for this document is pending.
        await self._pool.enqueue_job("ingest_document", document_id, _job_id=f"ingest:{document_id}")
