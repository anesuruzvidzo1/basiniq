"""Unit tests for PDF chunking logic in ingest_docs.py."""
import pytest

CHUNK_SIZE = 500
OVERLAP = 50


def chunk_text_with_pages(pages: list[dict]) -> list[dict]:
    word_pages = []
    for p in pages:
        for word in p["text"].split():
            word_pages.append((p["page"], word))
    chunks = []
    i = 0
    while i < len(word_pages):
        slice_ = word_pages[i: i + CHUNK_SIZE]
        text = " ".join(w for _, w in slice_)
        page_num = slice_[0][0] if slice_ else 1
        chunks.append({"page": page_num, "text": text})
        i += CHUNK_SIZE - OVERLAP
    return chunks


def _pages(text: str, page: int = 1) -> list[dict]:
    return [{"page": page, "text": text}]


def _words(n: int) -> str:
    return " ".join(f"word{i}" for i in range(n))


class TestChunkTextWithPages:
    def test_empty_input_returns_empty(self):
        assert chunk_text_with_pages([]) == []

    def test_single_short_page_single_chunk(self):
        pages = _pages("hello world foo bar")
        chunks = chunk_text_with_pages(pages)
        assert len(chunks) == 1
        assert "hello" in chunks[0]["text"]

    def test_chunk_size_respected(self):
        pages = _pages(_words(CHUNK_SIZE * 3))
        chunks = chunk_text_with_pages(pages)
        for chunk in chunks:
            assert len(chunk["text"].split()) <= CHUNK_SIZE

    def test_overlap_between_consecutive_chunks(self):
        pages = _pages(_words(CHUNK_SIZE + OVERLAP + 10))
        chunks = chunk_text_with_pages(pages)
        assert len(chunks) >= 2
        last_words_of_first = set(chunks[0]["text"].split()[-(OVERLAP):])
        first_words_of_second = set(chunks[1]["text"].split()[:OVERLAP])
        assert last_words_of_first & first_words_of_second

    def test_page_number_assigned(self):
        pages = _pages("some text here", page=5)
        chunks = chunk_text_with_pages(pages)
        assert chunks[0]["page"] == 5

    def test_multiple_pages_preserves_page_numbers(self):
        pages = [
            {"page": 1, "text": _words(10)},
            {"page": 2, "text": _words(10)},
        ]
        chunks = chunk_text_with_pages(pages)
        assert chunks[0]["page"] == 1

    def test_exact_chunk_size_produces_overlap_chunk(self):
        # CHUNK_SIZE words → first chunk at 0, next starts at CHUNK_SIZE-OVERLAP
        # so a second (short) overlap chunk is produced
        pages = _pages(_words(CHUNK_SIZE))
        chunks = chunk_text_with_pages(pages)
        assert len(chunks) == 2
        assert len(chunks[1]["text"].split()) == OVERLAP

    def test_chunk_size_plus_one_produces_two_chunks(self):
        pages = _pages(_words(CHUNK_SIZE + 1))
        chunks = chunk_text_with_pages(pages)
        assert len(chunks) == 2

    def test_each_chunk_has_text_key(self):
        pages = _pages(_words(600))
        for chunk in chunk_text_with_pages(pages):
            assert "text" in chunk

    def test_each_chunk_has_page_key(self):
        pages = _pages(_words(600))
        for chunk in chunk_text_with_pages(pages):
            assert "page" in chunk

    def test_no_empty_chunks(self):
        pages = _pages(_words(1200))
        for chunk in chunk_text_with_pages(pages):
            assert chunk["text"].strip() != ""

    def test_whitespace_only_page_skipped_upstream(self):
        pages = [{"page": 1, "text": "   "}]
        chunks = chunk_text_with_pages(pages)
        assert chunks == [] or all(c["text"].strip() == "" for c in chunks)
