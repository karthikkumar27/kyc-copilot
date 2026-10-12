import asyncio

from app.adapters.pii.regex import RegexRedactor


def test_malaysian_identifiers_are_redacted():
    text = ("IC 900101-14-5678 or 900101145678, call +60123456789 or 012-345 6789, "
            "email siti@example.com, card 4111 1111 1111 1111. Limit RM 50,000.")
    out = asyncio.run(RegexRedactor().redact(text))
    for secret in ["900101", "123456789", "345 6789", "siti@", "4111"]:
        assert secret not in out
    assert "<MY_NRIC>" in out and "<PHONE_NUMBER>" in out and "<EMAIL_ADDRESS>" in out
    assert "<CREDIT_CARD>" in out
    assert "RM 50,000" in out  # amounts are not PII
