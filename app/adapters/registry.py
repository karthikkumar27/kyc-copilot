"""Maps (adapter kind, provider name) -> implementation, imported lazily.

Lazy imports mean the local stack never needs cloud SDKs installed, and a GCP deploy never
imports AWS or Azure code.
"""

import importlib

_REGISTRY: dict[str, dict[str, str]] = {
    "ocr": {
        "local": "app.adapters.ocr.local:TesseractOCR",
        "gcp": "app.adapters.ocr.gcp:DocumentAIOCR",
        "aws": "app.adapters.ocr.aws:TextractOCR",
        "azure": "app.adapters.ocr.azure:DocumentIntelligenceOCR",
    },
    "pii": {
        "presidio": "app.adapters.pii.presidio:PresidioRedactor",
        "regex": "app.adapters.pii.regex:RegexRedactor",
        "gcp": "app.adapters.pii.gcp:SensitiveDataProtectionRedactor",
        "aws": "app.adapters.pii.aws:ComprehendRedactor",
        "azure": "app.adapters.pii.azure:AzureLanguagePIIRedactor",
    },
    "storage": {
        "local": "app.adapters.storage.local:LocalStorage",
        "gcp": "app.adapters.storage.gcp:GCSStorage",
        "aws": "app.adapters.storage.aws:S3Storage",
        "azure": "app.adapters.storage.azure:BlobStorage",
    },
    "queue": {
        "arq": "app.adapters.queue.arq_queue:ArqQueue",
        "gcp": "app.adapters.queue.gcp:CloudTasksQueue",
        "aws": "app.adapters.queue.aws:SQSQueue",
        "azure": "app.adapters.queue.azure:ServiceBusQueue",
    },
}


def available(kind: str) -> list[str]:
    return sorted(_REGISTRY.get(kind, {}))


def resolve(kind: str, name: str) -> type:
    try:
        target = _REGISTRY[kind][name]
    except KeyError:
        raise ValueError(
            f"Unknown {kind} provider '{name}'. Options: {available(kind)}"
        ) from None
    module_name, attr = target.split(":")
    return getattr(importlib.import_module(module_name), attr)
