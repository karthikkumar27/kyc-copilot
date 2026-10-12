from app.adapters._placeholder import PlannedProvider


class DocumentIntelligenceOCR(PlannedProvider):
    cloud = "Azure"
    service = "Azure AI Document Intelligence"
