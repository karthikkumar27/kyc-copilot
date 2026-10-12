from app.domain import PageText
from app.rag.chunking import chunk_pages


def test_sections_carry_over_and_respect_size():
    text = "# Attempt limits\n\n" + ("Customers get three attempts. " * 120) + "\n\n## DOC_BLURRY\n\nRetry on a dark surface."
    chunks = chunk_pages([PageText(1, text), PageText(2, "More text on page two.")], 500, 100)
    assert all(len(c.text) <= 500 for c in chunks)
    assert chunks[0].section == "Attempt limits"
    assert any(c.section == "DOC_BLURRY" and "dark surface" in c.text for c in chunks)
    last = chunks[-1]
    assert last.page == 2 and last.section == "DOC_BLURRY"  # section continues across pages
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_embedding_text_includes_section():
    chunks = chunk_pages([PageText(1, "# Tiers\n\nBASIC limit is RM 200.")])
    assert chunks[0].embedding_text().startswith("Tiers\n")


def test_empty_input_gives_no_chunks():
    assert chunk_pages([PageText(1, "   \n\n  ")]) == []
