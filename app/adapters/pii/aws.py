from app.adapters._placeholder import PlannedProvider


class ComprehendRedactor(PlannedProvider):
    cloud = "AWS"
    service = "Amazon Comprehend PII detection"
