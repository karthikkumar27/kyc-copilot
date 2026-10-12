import asyncio

from google.cloud import storage


class GCSStorage:
    def __init__(self, settings) -> None:
        if not settings.gcs_bucket:
            raise ValueError("GCS_BUCKET is required for STORAGE_PROVIDER=gcp")
        self._bucket = storage.Client(project=settings.gcp_project).bucket(settings.gcs_bucket)

    def _key(self, uri: str) -> str:
        prefix = f"gs://{self._bucket.name}/"
        if not uri.startswith(prefix):
            raise ValueError(f"URI is not in bucket {self._bucket.name}: {uri}")
        return uri[len(prefix):]

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        blob = self._bucket.blob(key)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)
        return f"gs://{self._bucket.name}/{key}"

    async def get(self, uri: str) -> bytes:
        return await asyncio.to_thread(self._bucket.blob(self._key(uri)).download_as_bytes)

    async def delete(self, uri: str) -> None:
        await asyncio.to_thread(self._bucket.blob(self._key(uri)).delete)
