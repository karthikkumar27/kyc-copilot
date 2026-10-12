import streamlit as st

from identity import ROLE_KEY
from scenario_data import FLASH_KEY, PENDING_SCENARIO_KEY, SCENARIOS, Scenario


def prepare(scenario: Scenario) -> None:
    """Button callback: runs before the next rerun, so it may set the sidebar's role widget."""
    if st.session_state.get(ROLE_KEY) != scenario.role:
        st.session_state[FLASH_KEY] = f"Role switched to {scenario.role}"
    st.session_state[ROLE_KEY] = scenario.role
    st.session_state[PENDING_SCENARIO_KEY] = scenario.id


st.title("Demo scenarios")
st.caption("Each scenario sets the role, opens the Ask page and asks its question.")

for scenario in SCENARIOS:
    with st.container(border=True):
        st.subheader(scenario.title)
        st.write(scenario.demonstrates)
        st.caption(f"Role: {scenario.role} · Customer: {scenario.customer_id or '—'}")
        st.text(scenario.question)
        st.caption(f"Look for: {scenario.look_for}")
        if st.button("Run", key=f"run_{scenario.id}", on_click=prepare, args=(scenario,)):
            st.switch_page("views/ask.py")
