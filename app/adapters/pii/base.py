from typing import Protocol


class PIIRedactor(Protocol):
    async def redact(self, text: str) -> str:
        """Return text with personal data replaced by placeholders such as <MY_NRIC>."""
        ...
