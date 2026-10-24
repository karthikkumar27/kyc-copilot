"""FR-OPS-03/04, INV-15: a forced 500 carries the real request id in body, header and log."""

import io
import logging

from fastapi.testclient import TestClient

from app.logging_setup import JsonFormatter
from app.main import app


@app.get("/_test/boom")
async def boom():
    raise RuntimeError("secret provider detail")


def test_unhandled_error_has_request_id_in_body_header_and_log():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(handler)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/_test/boom", headers={"x-request-id": "req-abc123"})
    finally:
        logging.getLogger().removeHandler(handler)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error", "request_id": "req-abc123"}
    assert response.headers["x-request-id"] == "req-abc123"
    assert "secret provider detail" not in response.text
    assert '"request_id": "req-abc123"' in stream.getvalue()


def test_unhandled_error_without_header_gets_a_generated_id():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/_test/boom")
    rid = response.json()["request_id"]
    assert rid != "-" and response.headers["x-request-id"] == rid
