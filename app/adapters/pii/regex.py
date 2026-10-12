"""Dependency-free redactor for tests and as a last line of defence.

Covers Malaysian identifiers that generic tools often miss (MyKad numbers, +60 mobiles).
"""

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL_ADDRESS", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("CREDIT_CARD", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")),
    ("MY_NRIC", re.compile(r"(?<!\d)\d{6}-?\d{2}-?\d{4}(?!\d)")),
    ("PHONE_NUMBER", re.compile(r"(?<![\d+])(?:\+?60|0)1\d[- ]?\d{3,4}[- ]?\d{4}(?!\d)")),
]


class RegexRedactor:
    def __init__(self, settings: object = None) -> None:
        pass

    def redact_sync(self, text: str) -> str:
        for label, pattern in _PATTERNS:
            text = pattern.sub(f"<{label}>", text)
        return text

    async def redact(self, text: str) -> str:
        return self.redact_sync(text)
