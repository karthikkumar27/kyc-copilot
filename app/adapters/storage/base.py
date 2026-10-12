from typing import Protocol


class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes and return a provider URI (file://..., gs://...)."""
        ...

    async def get(self, uri: str) -> bytes: ...

    async def delete(self, uri: str) -> None: ...
