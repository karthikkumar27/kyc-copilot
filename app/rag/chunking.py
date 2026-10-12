"""Heading-aware chunking that keeps page numbers (for citations) and section titles
(prepended at embedding time so short chunks keep their context)."""

import re
from dataclasses import dataclass

from app.domain import PageText

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+)$")
_BLANK_LINES = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class Chunk:
    index: int
    page: int
    section: str
    text: str

    def embedding_text(self) -> str:
        return f"{self.section}\n{self.text}" if self.section else self.text


def chunk_pages(pages: list[PageText], max_chars: int = 1500, overlap: int = 200) -> list[Chunk]:
    if overlap >= max_chars // 2:
        raise ValueError("overlap must be smaller than half of max_chars")
    chunks: list[Chunk] = []
    section = ""

    for page in pages:
        buffer: list[str] = []
        size = 0

        def flush() -> None:
            nonlocal buffer, size
            if buffer:
                chunks.append(Chunk(len(chunks), page.page, section, "\n\n".join(buffer)))
                buffer, size = [], 0

        for block in _blocks(page.text):
            lines = block.splitlines()
            heading = _HEADING.match(lines[0])
            if heading:
                flush()
                section = heading.group(1).strip()
                block = "\n".join(lines[1:]).strip()
                if not block:
                    continue
            for piece in _split_long(block, max_chars, overlap):
                if size and size + len(piece) + 2 > max_chars:
                    flush()
                buffer.append(piece)
                size += len(piece) + 2
        flush()
    return chunks


def _blocks(text: str) -> list[str]:
    return [b.strip() for b in _BLANK_LINES.split(text) if b.strip()]


def _split_long(block: str, max_chars: int, overlap: int) -> list[str]:
    """Split an oversized block at sentence or line boundaries, with overlap."""
    if len(block) <= max_chars:
        return [block]
    pieces: list[str] = []
    start, n = 0, len(block)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            cut = max(block.rfind(". ", start, end), block.rfind("\n", start, end))
            if cut > start + max_chars // 2:
                end = cut + 1
        piece = block[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= n:
            break
        start = end - overlap
        space = block.find(" ", start, end)
        if space != -1:
            start = space + 1
    return pieces
