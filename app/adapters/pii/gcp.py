"""PII redaction with Google Cloud Sensitive Data Protection (Cloud DLP)."""

from google.cloud import dlp_v2

from app.adapters.pii.regex import RegexRedactor

BUILT_IN = ["PERSON_NAME", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD_NUMBER", "IBAN_CODE"]


class SensitiveDataProtectionRedactor:
    def __init__(self, settings) -> None:
        if not settings.gcp_project:
            raise ValueError("GCP_PROJECT is required for PII_PROVIDER=gcp")
        self._client = dlp_v2.DlpServiceAsyncClient()
        self._parent = f"projects/{settings.gcp_project}/locations/{settings.dlp_location}"
        self._fallback = RegexRedactor()

    async def redact(self, text: str) -> str:
        if not text.strip():
            return text
        response = await self._client.deidentify_content(
            request={
                "parent": self._parent,
                "inspect_config": {
                    "info_types": [{"name": name} for name in BUILT_IN],
                    "custom_info_types": [
                        {
                            "info_type": {"name": "MY_NRIC"},
                            "regex": {"pattern": r"\d{6}-?\d{2}-?\d{4}"},
                        }
                    ],
                },
                "deidentify_config": {
                    "info_type_transformations": {
                        "transformations": [
                            {"primitive_transformation": {"replace_with_info_type_config": {}}}
                        ]
                    }
                },
                "item": {"value": text},
            }
        )
        return self._fallback.redact_sync(response.item.value)
