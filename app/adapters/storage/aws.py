from app.adapters._placeholder import PlannedProvider


class S3Storage(PlannedProvider):
    cloud = "AWS"
    service = "Amazon S3"
