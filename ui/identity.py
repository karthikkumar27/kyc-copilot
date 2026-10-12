"""Who is using the console.

Dev mode: the role and user ID are chosen in the sidebar and sent to the API as headers.
OIDC (roadmap project 2) will change how an Identity is produced; pages only ever see Identity.
"""

from dataclasses import dataclass

import streamlit as st

ROLES = ("agent", "supervisor", "admin")
ROLE_KEY = "role"
USER_ID_KEY = "user_id"


@dataclass(frozen=True)
class Identity:
    user_id: str
    role: str

    # Display hints only: the API enforces every permission.
    @property
    def can_manage_documents(self) -> bool:
        return self.role in ("supervisor", "admin")

    @property
    def can_delete_documents(self) -> bool:
        return self.role == "admin"


def current_identity() -> Identity:
    role = st.session_state.get(ROLE_KEY, "agent")
    user_id = (st.session_state.get(USER_ID_KEY) or "").strip() or f"ui-{role}"
    return Identity(user_id=user_id, role=role)


def render_dev_identity_controls() -> None:
    st.session_state.setdefault(ROLE_KEY, "agent")
    st.selectbox("Role", ROLES, key=ROLE_KEY)
    st.text_input("User ID", key=USER_ID_KEY, placeholder=f"ui-{st.session_state[ROLE_KEY]}")
    st.caption("Dev mode: identity is sent as headers, not for production.")
