from app.adapters._placeholder import PlannedProvider


class BlobStorage(PlannedProvider):
    cloud = "Azure"
    service = "Azure Blob Storage"
