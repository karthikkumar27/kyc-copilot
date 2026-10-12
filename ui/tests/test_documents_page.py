import pytest
from fakes import FakeClient, document, start

from api_client import ApiError

@pytest.mark.parametrize("role, can_manage, can_delete", [
    ("agent", False, False), ("supervisor", True, False), ("admin", True, True),
])
def test_document_controls_follow_role(role, can_manage, can_delete):
    at = start(FakeClient(documents=[document()]), role=role, page="pages/documents.py")
    labels = [b.label for b in at.button]
    assert ("Re-ingest" in labels) is can_manage
    assert ("Delete" in labels) is can_delete
    assert (len(at.expander) == 1) is can_manage  # the upload expander
    if not can_manage:
        assert any("requires supervisor or admin" in c.value for c in at.caption)


def test_failed_document_shows_its_error():
    failed = document(status="failed", error="ValueError: No text could be extracted")
    at = start(FakeClient(documents=[failed]), role="admin", page="pages/documents.py")
    table = at.dataframe[0].value
    assert table.loc[0, "Status"] == "❌ failed"
    assert table.loc[0, "Error"].startswith("ValueError")


def test_empty_knowledge_base_says_so():
    at = start(FakeClient(documents=[]), role="admin", page="pages/documents.py")
    assert any("No documents yet" in i.value for i in at.info)


def test_action_on_a_vanished_document_shows_the_error():
    gone = ApiError(404, "Document not found", "req404")
    at = start(FakeClient(documents=[document()], action_error=gone), role="admin",
               page="pages/documents.py")
    at.button(key="reingest").click().run()
    assert any("Document not found" in e.value for e in at.error)
    assert at.dataframe  # the page is still usable


def test_polling_switches_off_when_nothing_is_pending():
    client = FakeClient(documents=[document(status="queued")])
    at = start(client, role="admin", page="pages/documents.py")
    assert at.session_state["documents_polling"] is True
    client.documents = [document(status="ready")]
    at.run()
    assert at.session_state["documents_polling"] is False
