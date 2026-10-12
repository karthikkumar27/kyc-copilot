from typing import Protocol


class JobQueue(Protocol):
    async def enqueue_ingest(self, document_id: str) -> None: ...
