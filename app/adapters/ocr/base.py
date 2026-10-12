from typing import Protocol

from app.domain import PageText


class OCRProvider(Protocol):
    async def extract(self, data: bytes, mime_type: str) -> list[PageText]:
        """Return text per page for a PDF or image."""
        ...
