"""GCP queue: Cloud Tasks pushes to the worker Cloud Run service with an OIDC token.

The worker service only allows the API's service account to invoke it (Cloud Run IAM).
"""

from google.cloud import tasks_v2


class CloudTasksQueue:
    def __init__(self, settings) -> None:
        required = {
            "GCP_PROJECT": settings.gcp_project,
            "TASKS_QUEUE": settings.tasks_queue,
            "WORKER_URL": settings.worker_url,
            "TASKS_SERVICE_ACCOUNT": settings.tasks_service_account,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"QUEUE_PROVIDER=gcp requires: {', '.join(missing)}")
        self._client = tasks_v2.CloudTasksAsyncClient()
        self._parent = self._client.queue_path(
            settings.gcp_project, settings.tasks_location or settings.gcp_region, settings.tasks_queue
        )
        self._worker_url = settings.worker_url.rstrip("/")
        self._service_account = settings.tasks_service_account

    async def enqueue_ingest(self, document_id: str) -> None:
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{self._worker_url}/internal/ingest/{document_id}",
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=self._service_account, audience=self._worker_url
                ),
            )
        )
        await self._client.create_task(parent=self._parent, task=task)
