"""Deterministic disclosure policy for verification outcomes.

Some rejection reasons can be explained to the customer (a blurry photo). Others must never
be disclosed or hinted at, for example a sanctions-screening hit, because telling the customer
could amount to tipping-off under AML rules. This is enforced in code, not in the prompt: the
LLM never receives the internal reason, so no jailbreak can make it reveal it.
"""

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
    "speculate about any reason. Use script SCR-REVIEW-01 and escalate per SOP-ESC-03."
)

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
