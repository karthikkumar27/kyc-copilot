import streamlit as st

from api_client import ApiError, ApiUnavailable, Document
from components import show_error
from deps import get_client
from formatting import PENDING_STATUSES, escape_md, status_icon
from identity import ROLES, current_identity
from scenario_data import FLASH_KEY

POLL_SECONDS = 3
POLLING_KEY = "documents_polling"
FILE_TYPES = ["pdf", "png", "jpg", "jpeg", "md", "txt"]  # mirrors the API's allow-list
SOURCE_TYPES = ["sop", "regulation", "faq", "script"]


def table_rows(documents: list[Document]) -> list[dict]:
    return [
        {
            "Status": f"{status_icon(d.status)} {d.status}",
            "File": d.filename,
            "Type": d.source_type,
            "Roles": ", ".join(d.allowed_roles),
            "Chunks": d.chunk_count,
            "Created": d.created_at,
            "Error": d.error or "",
        }
        for d in documents
    ]


@st.dialog("Delete document")
def confirm_delete(document: Document) -> None:
    st.write(f"Delete **{escape_md(document.filename)}**? Its chunks and stored file will be "
             "removed permanently.")
    if st.button("Delete permanently", type="primary"):
        try:
            get_client().delete_document(document.id)
        except (ApiError, ApiUnavailable) as exc:
            show_error(exc)
            return
        st.session_state[FLASH_KEY] = f"Deleted {document.filename}"
        st.rerun()


def document_actions(documents: list[Document]) -> None:
    identity = current_identity()
    if not identity.can_manage_documents:
        return
    by_id = {d.id: d for d in documents}
    selected = st.selectbox("Selected document", list(by_id),
                            format_func=lambda doc_id: by_id[doc_id].filename)
    document = by_id[selected]
    left, right = st.columns(2)
    with left:
        if st.button("Re-ingest", key="reingest"):
            try:
                get_client().reingest(document.id)
            except (ApiError, ApiUnavailable) as exc:
                show_error(exc)
            else:
                st.toast(f"Re-ingest queued for {document.filename}")
                st.session_state[POLLING_KEY] = True
                st.rerun(scope="app")
        st.caption("On the local stack, a re-ingest within 1 hour of the last run may not start "
                   "(TSD T1).")
    with right:
        if identity.can_delete_documents and st.button("Delete", key="delete"):
            confirm_delete(document)


@st.fragment(run_every=POLL_SECONDS if st.session_state.get(POLLING_KEY) else None)
def documents_panel() -> None:
    st.button("⟳ Refresh")
    try:
        documents = get_client().list_documents()
    except (ApiError, ApiUnavailable) as exc:
        show_error(exc)
        return
    pending = any(d.status in PENDING_STATUSES for d in documents)
    if pending != st.session_state.get(POLLING_KEY, False):
        st.session_state[POLLING_KEY] = pending
        st.rerun(scope="app")  # turn polling on or off
    if not documents:
        st.info("No documents yet.")
        return
    st.dataframe(table_rows(documents), hide_index=True)
    document_actions(documents)


def upload_section() -> None:
    if not current_identity().can_manage_documents:
        st.caption("Uploading requires supervisor or admin.")
        return
    with st.expander("Upload document"):
        with st.form("upload_form", clear_on_submit=True):
            file = st.file_uploader("File", type=FILE_TYPES)
            roles = st.multiselect("Allowed roles", ROLES, default=list(ROLES))
            source_type = st.selectbox("Source type", SOURCE_TYPES)
            submitted = st.form_submit_button("Upload", type="primary")
        if not submitted:
            return
        if file is None or not roles:
            st.warning("Choose a file and at least one role.")
            return
        try:
            result = get_client().upload_document(file.name, file.getvalue(), roles, source_type)
        except (ApiError, ApiUnavailable) as exc:
            show_error(exc)
            return
        st.session_state[FLASH_KEY] = ("Already in the knowledge base (deduplicated)"
                                       if result.deduplicated else f"Queued {file.name}")
        st.session_state[POLLING_KEY] = not result.deduplicated
        st.rerun()


st.title("Knowledge base")
flash = st.session_state.pop(FLASH_KEY, None)
if flash:
    st.toast(flash)
documents_panel()
upload_section()
