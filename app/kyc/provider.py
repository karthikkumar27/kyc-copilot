"""Live account-status lookup (the 'real-time' part of the copilot).

The mock reads synthetic records from JSON. A real implementation would call the core
banking / e-KYC vendor API behind the same interface.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class KycStatusProvider(Protocol):
    async def get_status(self, tenant_id: str, customer_id: str) -> dict | None: ...


class MockKycStatusProvider:
    def __init__(self, path: str) -> None:
        records = json.loads(Path(path).read_text(encoding="utf-8"))
        self._records = {(r["tenant_id"], r["customer_id"]): r for r in records}

    async def get_status(self, tenant_id: str, customer_id: str) -> dict | None:
        return self._records.get((tenant_id, customer_id))


@lru_cache
def get_kyc_provider() -> KycStatusProvider:
    s = get_settings()
    if s.kyc_status_provider == "mock":
        return MockKycStatusProvider(s.kyc_mock_data_path)
    raise ValueError(f"Unknown KYC_STATUS_PROVIDER '{s.kyc_status_provider}'")
