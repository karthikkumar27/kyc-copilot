from app.kyc.policy import RESTRICTED_AGENT_NOTICE, build_account_context, guard_restricted_output

BASE = {"customer_id": "CUS-10001", "verification_tier": "BASIC", "attempts_used": 1,
        "attempts_max": 3, "secret_internal_field": "x"}


def test_disclosable_reason_is_explained():
    ctx, notice = build_account_context({**BASE, "verification_status": "REJECTED",
                                         "reason_code": "DOC_BLURRY"})
    assert notice is None
    assert ctx["reason_code"] == "DOC_BLURRY" and "not clear" in ctx["reason_explanation"]
    assert "secret_internal_field" not in ctx


def test_internal_reason_never_reaches_the_model():
    for code in ["SANCTIONS_SCREENING_HIT", "FRAUD_SUSPECTED", "SOME_NEW_CODE"]:  # unknown fails closed
        ctx, notice = build_account_context({**BASE, "verification_status": "REJECTED",
                                             "reason_code": code})
        assert notice == RESTRICTED_AGENT_NOTICE
        assert ctx["verification_status"] == "UNDER_REVIEW"
        assert code not in str(ctx)
        assert "SCR-REVIEW-01" in ctx["disclosure_rule"]


def test_verified_customer_has_no_notice():
    ctx, notice = build_account_context({**BASE, "verification_status": "VERIFIED", "reason_code": None})
    assert notice is None and ctx["verification_status"] == "VERIFIED"


def test_guard_replaces_restricted_terms_in_answer_and_reply():
    for term in ["sanctions", "SANCTION", "Screening", "screened for fraud", "a Watchlist match",
                 "Fraudulent"]:
        answer, reply, fields = guard_restricted_output(f"Note: {term} apply.", f"Dear, {term}.")
        assert answer == RESTRICTED_AGENT_NOTICE and reply == ""
        assert fields == ["answer", "suggested_reply"]


def test_guard_changes_only_the_field_that_hits():
    answer, reply, fields = guard_restricted_output("Use SCR-REVIEW-01 and escalate.", "x watchlist")
    assert answer == "Use SCR-REVIEW-01 and escalate." and reply == "" and fields == ["suggested_reply"]


def test_guard_leaves_clean_output_alone():
    out = guard_restricted_output("Escalate to Compliance Review.", "We are reviewing your case.")
    assert out == ("Escalate to Compliance Review.", "We are reviewing your case.", [])


def test_guard_catches_obfuscated_spellings():
    for text in ["s a n c t i o n s", "sanc​tions", "ＳＡＮＣＴＩＯＮ", "watch-list", "Watch List",
                 "f.r.a.u.d", "screen­ING", "SANCTIONS".lower().upper()]:
        assert guard_restricted_output(text, "ok")[0] == RESTRICTED_AGENT_NOTICE, text


def test_guard_ignores_ordinary_restricted_case_wording():
    text = "Escalate to Compliance Review. Use SCR-REVIEW-01 and wait for the review to finish."
    assert guard_restricted_output(text, text) == (text, text, [])


def test_restricted_notice_names_the_script_and_compliance_review():  # BR-04, g004
    assert "SCR-REVIEW-01" in RESTRICTED_AGENT_NOTICE
    assert "escalate to Compliance Review" in RESTRICTED_AGENT_NOTICE
