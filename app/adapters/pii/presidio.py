"""Local PII redaction with Microsoft Presidio plus Malaysian recognizers.

Note: the small spaCy model is weak at Malay names. Measure recall on your golden set and
consider a larger or multilingual model before relying on PERSON detection.
"""

import asyncio

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from app.adapters.pii.regex import RegexRedactor

ENTITIES = [
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IBAN_CODE", "MY_NRIC", "MY_PHONE",
]


class PresidioRedactor:
    def __init__(self, settings: object = None) -> None:
        nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        ).create_engine()
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        self._analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="MY_NRIC",
                patterns=[Pattern("mykad", r"(?<!\d)\d{6}-?\d{2}-?\d{4}(?!\d)", 0.7)],
            )
        )
        self._analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="MY_PHONE",
                patterns=[Pattern("my_mobile", r"(?:\+?60|0)1\d[- ]?\d{3,4}[- ]?\d{4}", 0.6)],
            )
        )
        self._anonymizer = AnonymizerEngine()
        self._fallback = RegexRedactor()

    def _redact_sync(self, text: str) -> str:
        results = self._analyzer.analyze(text=text, language="en", entities=ENTITIES)
        redacted = self._anonymizer.anonymize(text=text, analyzer_results=results).text
        # Defence in depth: deterministic patterns catch anything the model missed.
        return self._fallback.redact_sync(redacted)

    async def redact(self, text: str) -> str:
        return await asyncio.to_thread(self._redact_sync, text)
