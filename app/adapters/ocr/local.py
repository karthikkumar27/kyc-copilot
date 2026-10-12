"""Local OCR: text layer via pypdf, Tesseract (English + Malay) for scanned pages and images."""

import asyncio
import io

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from pypdf import PdfReader

from app.domain import PageText

MIN_TEXT_CHARS = 20  # below this, treat a PDF page as scanned and OCR it


class TesseractOCR:
    def __init__(self, settings: object = None, languages: str = "eng+msa") -> None:
        self.languages = languages

    async def extract(self, data: bytes, mime_type: str) -> list[PageText]:
        return await asyncio.to_thread(self._extract_sync, data, mime_type)

    def _extract_sync(self, data: bytes, mime_type: str) -> list[PageText]:
        if mime_type == "application/pdf":
            return self._pdf(data)
        if mime_type.startswith("image/"):
            image = Image.open(io.BytesIO(data))
            return [PageText(1, pytesseract.image_to_string(image, lang=self.languages))]
        raise ValueError(f"Unsupported mime type for OCR: {mime_type}")

    def _pdf(self, data: bytes) -> list[PageText]:
        reader = PdfReader(io.BytesIO(data))
        pages: list[PageText] = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) < MIN_TEXT_CHARS:
                images = convert_from_bytes(data, first_page=number, last_page=number, dpi=300)
                text = pytesseract.image_to_string(images[0], lang=self.languages) if images else ""
            pages.append(PageText(number, text))
        return pages
