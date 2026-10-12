import streamlit as st

from api_client import ApiError, ApiUnavailable, AskResult, validate_ask_input
from components import show_error
from deps import get_client
from formatting import citation_line, escape_md, history_title, latency_text, short_id
from identity import current_identity
from scenario_data import FLASH_KEY, PENDING_SCENARIO_KEY, SCENARIOS_BY_ID

HISTORY_KEY = "ask_history"
HISTORY_LIMIT = 20
QUESTION_KEY = "ask_question"
CUSTOMER_KEY = "ask_customer"


def render_result(result: AskResult) -> None:
    if result.agent_notice:  # first, so an agent cannot miss it
        st.error(f"⛔ **Restricted case.** {escape_md(result.agent_notice)}")
    badges = []
    if result.needs_escalation:
        badges.append(":orange-badge[⚠️ Escalate]")
    if result.insufficient_context:
        badges.append(":blue-badge[ℹ️ Insufficient context]")
    if badges:
        st.markdown(" ".join(badges))
    model = escape_md(result.model) if result.model else "no model call"
    st.caption(f"{model} · {latency_text(result.latency_ms)} · request "
               f"{escape_md(short_id(result.request_id))}")
    st.subheader("Answer")
    st.text(result.answer)  # model output: never parsed as Markdown or HTML (OWASP LLM05)
    if result.citations:
        st.subheader("Sources")
        for citation in result.citations:
            st.text(citation_line(citation))
    if result.suggested_reply:
        st.subheader("Suggested reply")
        st.code(result.suggested_reply, language=None, wrap_lines=True)


def ask_and_record(question: str, customer_id: str, look_for: str | None) -> bool:
    role = current_identity().role
    try:
        with st.spinner("Asking the copilot…"):
            result = get_client().ask(question, customer_id or None)
    except (ApiError, ApiUnavailable) as exc:
        show_error(exc)
        return False
    history = st.session_state.setdefault(HISTORY_KEY, [])
    history.insert(0, {"title": history_title(role, customer_id, question),
                       "result": result, "look_for": look_for})
    del history[HISTORY_LIMIT:]
    return True


st.title("Ask the copilot")

flash = st.session_state.pop(FLASH_KEY, None)
if flash:
    st.toast(flash)

scenario = SCENARIOS_BY_ID.get(st.session_state.pop(PENDING_SCENARIO_KEY, None) or "")
if scenario:  # set before the widgets exist, so they show the scenario's values
    st.session_state[QUESTION_KEY] = scenario.question
    st.session_state[CUSTOMER_KEY] = scenario.customer_id

with st.form("ask_form"):
    st.text_area("Question", key=QUESTION_KEY, max_chars=2000)
    st.text_input("Customer reference (optional)", key=CUSTOMER_KEY, placeholder="CUS-12345")
    submitted = st.form_submit_button("Ask", type="primary")

failed = False  # a failed ask must not leave an older answer looking current
if submitted or scenario:
    question = st.session_state[QUESTION_KEY].strip()
    customer_id = st.session_state[CUSTOMER_KEY].strip()
    errors = validate_ask_input(question, customer_id)
    for message in errors:
        st.warning(message)
    failed = bool(errors) or not ask_and_record(
        question, customer_id, scenario.look_for if scenario else None)

history = st.session_state.get(HISTORY_KEY, [])
if history:
    latest, earlier = (None, history) if failed else (history[0], history[1:])
    if latest:
        if latest["look_for"]:
            st.info(f"Look for: {escape_md(latest['look_for'])}")
        st.caption(escape_md(latest["title"]))  # which question and customer this answers
        render_result(latest["result"])
    if earlier:
        st.divider()
        st.subheader("Earlier in this session")
        for entry in earlier:
            with st.expander(escape_md(entry["title"])):
                render_result(entry["result"])
