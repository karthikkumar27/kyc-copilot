from app.adapters._placeholder import PlannedProvider


class TextractOCR(PlannedProvider):
    cloud = "AWS"
    service = "Amazon Textract"
