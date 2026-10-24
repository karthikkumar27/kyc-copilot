"""Deterministic disclosure policy for verification outcomes.

Some rejection reasons can be explained to the customer (a blurry photo). Others must never
be disclosed or hinted at, for example a sanctions-screening hit, because telling the customer
could amount to tipping-off under AML rules. This is enforced in code, not in the prompt: the
LLM never receives the internal reason, so no jailbreak can make it reveal it.
"""

import unicodedata

CUSTOMER_DISCLOSABLE: dict[str, str] = {
    "DOC_BLURRY": "The photo of the ID document was not clear enough to read.",
    "DOC_EXPIRED": "The ID document submitted had expired.",
    "DOC_GLARE": "Light glare covered part of the ID document.",
    "NAME_MISMATCH": "The name entered in the app did not match the ID document.",
    "SELFIE_MISMATCH": "The selfie could not be matched to the photo on the ID document.",
    "LIVENESS_FAILED": "The liveness check (the short selfie video) could not be completed.",
    "UNSUPPORTED_DOC": "The document type submitted is not accepted for verification.",
}

# Anything not in CUSTOMER_DISCLOSABLE is treated as internal-only (fail closed).
INTERNAL_ONLY_EXAMPLES = {"COMPLIANCE_REVIEW", "SANCTIONS_SCREENING_HIT", "FRAUD_SUSPECTED",
                          "DUPLICATE_IDENTITY"}

RESTRICTED_SCRIPT_ID = "SCR-REVIEW-01"
RESTRICTED_AGENT_NOTICE = (
    "Restricted case: this verification is under internal review. Do not state, confirm or "
    "speculate about any reason. Use script SCR-REVIEW-01 and escalate to Compliance Review "
    "per SOP-ESC-03."
)

# BR-09: model output for a restricted case must not contain these (matched case-insensitively
# anywhere in the text), whatever the question said. Output only; the model never gets the reason.
RESTRICTED_OUTPUT_TERMS = ("sanction", "screening", "watchlist", "fraud")

SAFE_FIELDS = (
    "customer_id", "verification_status", "verification_tier", "document_type",
    "attempts_used", "attempts_max", "last_attempt_at", "display_name_masked",
)


def build_account_context(record: dict) -> tuple[dict, str | None]:
    """Return (context the LLM may see, notice shown only to the support agent)."""
    context = {field: record.get(field) for field in SAFE_FIELDS if field in record}
    status = record.get("verification_status")
    reason = record.get("reason_code")

    if status in {"REJECTED", "UNDER_REVIEW"} and reason:
        if reason in CUSTOMER_DISCLOSABLE:
            context["reason_code"] = reason
            context["reason_explanation"] = CUSTOMER_DISCLOSABLE[reason]
            return context, None
        context["verification_status"] = "UNDER_REVIEW"
        context["disclosure_rule"] = (
            f"Internal review. Do not give or guess a reason. Use script {RESTRICTED_SCRIPT_ID}."
        )
        return context, RESTRICTED_AGENT_NOTICE

    return context, None


def guard_restricted_output(answer: str, suggested_reply: str) -> tuple[str, str, list[str]]:
    """BR-09: for a restricted case, replace any output field that names a withheld topic.

    The answer becomes the fixed agent notice; the customer reply is emptied so the agent uses
    SCR-REVIEW-01 word for word. Returns (answer, reply, names of the fields replaced).
    """
    def hit(text: str) -> bool:
        # NFKC folds full-width forms; dropping invisible (Cf), space (Z*) and -_. characters
        # catches "s a n c t i o n", "watch-list" and zero-width tricks.
        # shortcut: look-alike letters from other scripts (e.g. Cyrillic) are not folded; use a
        # confusables table if that becomes a real attack path.
        folded = "".join(
            ch for ch in unicodedata.normalize("NFKC", text).casefold()
            if unicodedata.category(ch)[0] not in "ZC" and ch not in "-_."
        )
        return any(term in folded for term in RESTRICTED_OUTPUT_TERMS)

    guarded = []
    if hit(answer):
        answer = RESTRICTED_AGENT_NOTICE
        guarded.append("answer")
    if hit(suggested_reply):
        suggested_reply = ""
        guarded.append("suggested_reply")
    return answer, suggested_reply, guarded
