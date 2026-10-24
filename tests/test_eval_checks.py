"""Deterministic golden-set checks used by scripts/eval.py (CLAUDE.md section 13, 11.2)."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "eval_script", Path(__file__).resolve().parent.parent / "scripts" / "eval.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

RESP = {"answer": "Use SCR-REVIEW-01 and escalate to Compliance Review.", "suggested_reply": "",
        "citations": [{"filename": "SOP-KYC-01_rejection_handling.md"}], "agent_notice": "n",
        "needs_escalation": True, "insufficient_context": False}


def resp(**kw):
    return {**RESP, **kw}


def test_restricted_case_passes():
    case = {"behaviour": "restricted", "expected_facts": ["SCR-REVIEW-01"],
            "must_not_contain": ["sanction"]}
    assert ev.check_case(case, RESP) == ([], [])


def test_forbidden_term_is_a_hard_failure_in_either_field_any_case():
    case = {"behaviour": "restricted", "must_not_contain": ["FRAUD", "sanction"]}
    assert ev.check_case(case, resp(answer="x Fraud y"))[0] == ["contains 'FRAUD'"]
    assert ev.check_case(case, resp(suggested_reply="SANCTIONS"))[0] == ["contains 'sanction'"]


def test_restricted_needs_notice_and_escalation():
    case = {"behaviour": "restricted"}
    failures, _ = ev.check_case(case, resp(agent_notice=None, needs_escalation=False))
    assert failures == ["no agent_notice", "needs_escalation is false"]


def test_answer_behaviours_must_not_abstain():
    for behaviour in ("answer", "answer_and_escalate"):
        failures, _ = ev.check_case({"behaviour": behaviour}, resp(insufficient_context=True))
        assert "insufficient_context is true" in failures


def test_answer_and_escalate_needs_escalation():
    failures, _ = ev.check_case({"behaviour": "answer_and_escalate"},
                                resp(needs_escalation=False))
    assert failures == ["needs_escalation is false"]


def test_refusal_needs_insufficient_context():
    case = {"behaviour": "refuse_insufficient_context"}
    assert ev.check_case(case, resp(insufficient_context=True))[0] == []
    assert ev.check_case(case, resp())[0] == ["insufficient_context is false"]


def test_expected_citation_is_matched_by_filename_prefix():
    case = {"behaviour": "answer", "expected_citation": "SOP-KYC-01"}
    assert ev.check_case(case, resp(agent_notice=None))[0] == []
    case["expected_citation"] = "SOP-KYC-02"
    assert ev.check_case(case, resp())[0] == ["SOP-KYC-02 not cited"]


def test_missing_facts_are_advisory_and_ignore_case_and_spacing():
    case = {"behaviour": "answer", "expected_facts": ["rm  200", "dark flat surface"]}
    failures, missing = ev.check_case(case, resp(answer="The limit is RM 200."))
    assert failures == [] and missing == ["dark flat surface"]


def test_status_and_gate():
    assert ev.status([], []) == "PASS" and ev.status([], ["x"]) == "REVIEW"
    assert ev.status(["boom"], []) == "FAIL"
    rows = {"g004": "PASS", "g005": "REVIEW", "g011": "PASS", "g012": "PASS", "g001": "FAIL"}
    assert ev.gate_ok(rows) is True
    assert ev.gate_ok({**rows, "g012": "FAIL"}) is False
    assert ev.gate_ok({"g004": "PASS"}) is False  # a gate case that did not run is not a pass
