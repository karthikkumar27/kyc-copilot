import asyncio
from pathlib import Path


class LocalStorage:
    def __init__(self, settings) -> None:
        self.root = Path(settings.local_storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, uri_or_key: str) -> Path:
        key = uri_or_key.removeprefix("file://")
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Path escapes storage root")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return f"file://{key}"

    async def get(self, uri: str) -> bytes:
        return await asyncio.to_thread(self._path(uri).read_bytes)

    async def delete(self, uri: str) -> None:
        await asyncio.to_thread(self._path(uri).unlink, missing_ok=True)
