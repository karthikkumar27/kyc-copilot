"""GCP ingestion worker: Cloud Tasks POSTs here. Cloud Run IAM ensures only the API's
service account can invoke this service. A non-2xx response makes Cloud Tasks retry."""

import uuid

from fastapi import FastAPI

from app.logging_setup import configure_logging
from app.rag.ingest import ingest_document

configure_logging()
app = FastAPI(title="KYC Copilot ingestion worker")


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/internal/ingest/{document_id}")
async def ingest(document_id: uuid.UUID) -> dict:
    await ingest_document(str(document_id))
    return {"status": "ok", "document_id": str(document_id)}
