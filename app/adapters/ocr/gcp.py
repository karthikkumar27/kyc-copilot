"""GCP OCR via Document AI.

Data residency: Document AI processors live in specific locations (check the current list).
Sending KYC documents to a processor outside your residency region may breach policy, which
is why the GCP Terraform defaults OCR_PROVIDER to "local" and makes Document AI opt-in.
"""

from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from app.domain import PageText


class DocumentAIOCR:
    def __init__(self, settings) -> None:
        if not (settings.gcp_project and settings.docai_processor_id):
            raise ValueError("GCP_PROJECT and DOCAI_PROCESSOR_ID are required for OCR_PROVIDER=gcp")
        endpoint = f"{settings.docai_location}-documentai.googleapis.com"
        self._client = documentai.DocumentProcessorServiceAsyncClient(
            client_options=ClientOptions(api_endpoint=endpoint)
        )
        self._name = self._client.processor_path(
            settings.gcp_project, settings.docai_location, settings.docai_processor_id
        )

    async def extract(self, data: bytes, mime_type: str) -> list[PageText]:
        request = documentai.ProcessRequest(
            name=self._name, raw_document=documentai.RawDocument(content=data, mime_type=mime_type)
        )
        result = await self._client.process_document(request=request)
        doc = result.document
        return [
            PageText(page.page_number, _layout_text(doc.text, page.layout)) for page in doc.pages
        ]


def _layout_text(full_text: str, layout) -> str:
    return "".join(
        full_text[int(seg.start_index) : int(seg.end_index)]
        for seg in layout.text_anchor.text_segments
    )
