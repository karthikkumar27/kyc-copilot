import pytest
from fakes import FakeClient, document, start

from api_client import ApiError

@pytest.mark.parametrize("role, can_manage, can_delete", [
    ("agent", False, False), ("supervisor", True, False), ("admin", True, True),
])
def test_document_controls_follow_role(role, can_manage, can_delete):
    at = start(FakeClient(documents=[document()]), role=role, page="views/documents.py")
    labels = [b.label for b in at.button]
    assert ("Re-ingest" in labels) is can_manage
    assert ("Delete" in labels) is can_delete
    assert (len(at.expander) == 1) is can_manage  # the upload expander
    if not can_manage:
        assert any("requires supervisor or admin" in c.value for c in at.caption)


def test_failed_document_shows_its_error():
    failed = document(status="failed", error="ValueError: No text could be extracted")
    at = start(FakeClient(documents=[failed]), role="admin", page="views/documents.py")
    table = at.dataframe[0].value
    assert table.loc[0, "Status"] == "❌ failed"
    assert table.loc[0, "Error"].startswith("ValueError")


def test_empty_knowledge_base_says_so():
    at = start(FakeClient(documents=[]), role="admin", page="views/documents.py")
    assert any("No documents yet" in i.value for i in at.info)


def test_action_on_a_vanished_document_shows_the_error():
    gone = ApiError(404, "Document not found", "req404")
    at = start(FakeClient(documents=[document()], action_error=gone), role="admin",
               page="views/documents.py")
    at.button(key="reingest").click().run()
    assert any("Document not found" in e.value for e in at.error)
    assert at.dataframe  # the page is still usable


def test_polling_switches_off_when_nothing_is_pending():
    client = FakeClient(documents=[document(status="queued")])
    at = start(client, role="admin", page="views/documents.py")
    assert at.session_state["documents_polling"] is True
    client.documents = [document(status="ready")]
    at.run()
    assert at.session_state["documents_polling"] is False


def test_delete_asks_for_confirmation_then_deletes():
    client = FakeClient(documents=[document()])
    at = start(client, role="admin", page="views/documents.py")
    at.button(key="delete").click().run()
    assert client.deletes == []
    next(b for b in at.button if b.label == "Delete permanently").click().run()
    assert client.deletes == ["d1"]


def test_documents_with_the_same_name_can_be_told_apart():
    docs = [document(id="d1aaaaaaaa", created_at="2026-10-12T10:00:00Z"),
            document(id="d2bbbbbbbb", created_at="2026-10-13T09:30:00Z")]
    at = start(FakeClient(documents=docs), role="admin", page="views/documents.py")
    options = at.selectbox[0].options
    assert len(set(options)) == 2


def test_filenames_in_notifications_are_escaped():
    evil = document(filename="[x](http://evil.example).md")
    at = start(FakeClient(documents=[evil]), role="admin", page="views/documents.py")
    at.button(key="reingest").click().run()
    toasts = [t.value for t in at.toast]
    assert toasts and all("](" not in t for t in toasts)
