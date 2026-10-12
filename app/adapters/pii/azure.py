from app.adapters._placeholder import PlannedProvider


class AzureLanguagePIIRedactor(PlannedProvider):
    cloud = "Azure"
    service = "Azure AI Language PII"
