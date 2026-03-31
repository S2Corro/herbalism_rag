# ---
# title: "Unit Tests — HerbChunk Domain Model"
# sprint: SPR-002
# task: T-005
# author: Developer Agent
# ---
"""Unit tests for the HerbChunk dataclass.

Tests cover construction, to_source() excerpt truncation,
to_chroma_metadata() serialization, and from_chroma() round-trip.
"""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from backend.models.herb_chunk import HerbChunk


def _make_chunk(**overrides: object) -> HerbChunk:
    """Create a HerbChunk with sensible defaults for testing."""
    defaults = {
        "id": "pubmed-123-chunk-0",
        "text": "Ashwagandha significantly reduced serum cortisol levels in stressed adults.",
        "source_type": "PubMed",
        "title": "Adaptogenic Effects of Ashwagandha",
        "url": "https://pubmed.ncbi.nlm.nih.gov/23439798/",
        "year": "2012",
        "herbs": ["Ashwagandha", "Withania somnifera"],
        "chunk_index": 0,
    }
    defaults.update(overrides)
    return HerbChunk(**defaults)  # type: ignore[arg-type]


def test_herb_chunk_construction() -> None:
    """HerbChunk should construct with all required fields."""
    chunk = _make_chunk()
    assert chunk.id == "pubmed-123-chunk-0"
    assert chunk.source_type == "PubMed"
    assert chunk.herbs == ["Ashwagandha", "Withania somnifera"]
    assert chunk.chunk_index == 0


def test_to_source_returns_correct_keys() -> None:
    """to_source() should return dict with expected keys."""
    src = _make_chunk().to_source()
    expected_keys = {"source_type", "title", "url", "year", "excerpt"}
    assert set(src.keys()) == expected_keys


def test_to_source_truncates_excerpt_to_300_chars() -> None:
    """to_source() excerpt must be at most 300 characters."""
    long_text = "A" * 500
    chunk = _make_chunk(text=long_text)
    src = chunk.to_source()
    assert len(src["excerpt"]) == 300
    assert src["excerpt"] == "A" * 300


def test_to_source_short_text_not_padded() -> None:
    """to_source() should not pad short text to 300 chars."""
    chunk = _make_chunk(text="Short text")
    src = chunk.to_source()
    assert src["excerpt"] == "Short text"


def test_to_chroma_metadata_herbs_as_csv() -> None:
    """to_chroma_metadata() must serialize herbs as comma-separated string."""
    chunk = _make_chunk(herbs=["Ginger", "Turmeric", "Curcumin"])
    meta = chunk.to_chroma_metadata()
    assert meta["herbs"] == "Ginger,Turmeric,Curcumin"
    assert isinstance(meta["herbs"], str)


def test_to_chroma_metadata_excludes_text() -> None:
    """to_chroma_metadata() must not include 'text' — it's stored as document."""
    meta = _make_chunk().to_chroma_metadata()
    assert "text" not in meta
    assert "id" not in meta


def test_from_chroma_round_trip() -> None:
    """from_chroma(to_chroma_metadata()) should reconstruct the original chunk."""
    original = _make_chunk()
    meta = original.to_chroma_metadata()
    restored = HerbChunk.from_chroma(
        id=original.id,
        document=original.text,
        metadata=meta,
    )
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.source_type == original.source_type
    assert restored.title == original.title
    assert restored.url == original.url
    assert restored.year == original.year
    assert restored.herbs == original.herbs
    assert restored.chunk_index == original.chunk_index


def test_from_chroma_empty_herbs() -> None:
    """from_chroma() with empty herbs string produces empty list, not ['']."""
    restored = HerbChunk.from_chroma(
        id="test",
        document="text",
        metadata={"herbs": "", "source_type": "PubMed", "title": "T",
                  "url": "u", "year": "2024", "chunk_index": 0},
    )
    assert restored.herbs == []
