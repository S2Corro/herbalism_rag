"""Unit tests for the sentence-aware text chunker."""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from backend.ingest.chunker import chunk_text


def test_chunker_splits_long_text() -> None:
    """A 1000-word text should be split into 2-3 chunks of ~512 tokens."""
    sentence = "Ashwagandha reduces cortisol and improves stress resilience. "
    text = sentence * 60  # ~540 words
    chunks = chunk_text(text, max_tokens=300, overlap_tokens=30, min_tokens=50)
    assert len(chunks) >= 2, f"Expected >=2 chunks, got {len(chunks)}"


def test_chunker_sentence_boundaries() -> None:
    """No chunk should end mid-sentence (must end with punctuation)."""
    text = (
        "First sentence here. Second sentence follows. "
        "Third sentence now. Fourth sentence added. "
        "Fifth sentence more. Sixth sentence extra text here."
    )
    chunks = chunk_text(text, max_tokens=10, overlap_tokens=3, min_tokens=3)
    for chunk in chunks:
        # Each chunk should end with a sentence-ending character
        assert chunk.rstrip().endswith((".", "!", "?")), (
            f"Chunk does not end at sentence boundary: ...{chunk[-30:]}"
        )


def test_chunker_overlap_present() -> None:
    """Consecutive chunks should share overlapping words."""
    sentence = "Word number one sentence here. "
    text = sentence * 40  # ~200 words
    chunks = chunk_text(text, max_tokens=80, overlap_tokens=20, min_tokens=10)
    assert len(chunks) >= 2
    # Last words of chunk 0 should appear in start of chunk 1
    c0_tail = set(chunks[0].split()[-20:])
    c1_head = set(chunks[1].split()[:30])
    overlap = c0_tail & c1_head
    assert len(overlap) > 0, "No overlap found between consecutive chunks"


def test_chunker_discards_short_fragments() -> None:
    """Fragments shorter than min_tokens should be discarded."""
    short_text = "Just a few words."
    chunks = chunk_text(short_text, min_tokens=100)
    assert chunks == []


def test_chunker_single_sentence() -> None:
    """A single sentence shorter than max_tokens should not be split."""
    text = "This is one complete sentence with enough words."
    chunks = chunk_text(text, max_tokens=512, min_tokens=5)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunker_empty_input() -> None:
    """Empty or whitespace input should return empty list."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []
