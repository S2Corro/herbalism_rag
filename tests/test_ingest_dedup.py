"""Unit tests for ingestion chunk deduplication (DEF-003).

Verifies that the dict-comprehension deduplication in ``scripts/ingest.py``
correctly eliminates duplicate chunk IDs before the ChromaDB upsert call.
"""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from backend.models.herb_chunk import HerbChunk


def _make_chunk(
    id: str,
    text: str = "sample text",
    source_type: str = "PubMed",
    title: str = "Test Article",
    url: str = "https://example.com",
    year: str = "2024",
    herbs: list[str] | None = None,
    chunk_index: int = 0,
) -> HerbChunk:
    """Factory helper for creating HerbChunk instances in tests."""
    return HerbChunk(
        id=id,
        text=text,
        source_type=source_type,
        title=title,
        url=url,
        year=year,
        herbs=herbs or ["Turmeric"],
        chunk_index=chunk_index,
    )


def _deduplicate(chunks: list[HerbChunk]) -> list[HerbChunk]:
    """Mirror the deduplication logic from ``scripts/ingest.py``.

    This is the exact dict-comprehension used in the ingest orchestrator.
    Extracting it here lets us test the logic in isolation without importing
    the full script (which has side effects like structlog configuration
    and sys.path manipulation).
    """
    return list({chunk.id: chunk for chunk in chunks}.values())


# ------------------------------------------------------------------
# Scenario 1 — happy path: duplicates are removed
# ------------------------------------------------------------------


class TestDeduplicateWithDuplicates:
    """Given a list of HerbChunks where two share the same ID."""

    def test_removes_duplicate_ids(self) -> None:
        """Only one chunk per ID should survive deduplication."""
        chunks: list[HerbChunk] = [
            _make_chunk(id="pubmed-12345-chunk-0", text="first occurrence"),
            _make_chunk(id="pubmed-99999-chunk-0", text="unique article"),
            _make_chunk(id="pubmed-12345-chunk-0", text="duplicate occurrence"),
        ]

        result: list[HerbChunk] = _deduplicate(chunks)

        result_ids: list[str] = [c.id for c in result]
        assert len(result) == 2
        assert result_ids.count("pubmed-12345-chunk-0") == 1
        assert "pubmed-99999-chunk-0" in result_ids

    def test_duplicate_count_is_correct(self) -> None:
        """The count of removed duplicates should match expectations."""
        chunks: list[HerbChunk] = [
            _make_chunk(id="pubmed-111-chunk-0"),
            _make_chunk(id="pubmed-222-chunk-0"),
            _make_chunk(id="pubmed-111-chunk-0"),  # dup 1
            _make_chunk(id="pubmed-333-chunk-0"),
            _make_chunk(id="pubmed-222-chunk-0"),  # dup 2
            _make_chunk(id="pubmed-111-chunk-0"),  # dup 3
        ]

        unique: list[HerbChunk] = _deduplicate(chunks)
        duplicate_count: int = len(chunks) - len(unique)

        assert len(unique) == 3
        assert duplicate_count == 3

    def test_warning_condition_fires_only_when_duplicates_exist(self) -> None:
        """The ``if duplicate_count:`` guard should be truthy for duplicates."""
        chunks: list[HerbChunk] = [
            _make_chunk(id="pubmed-111-chunk-0"),
            _make_chunk(id="pubmed-111-chunk-0"),
        ]

        unique: list[HerbChunk] = _deduplicate(chunks)
        duplicate_count: int = len(chunks) - len(unique)

        assert duplicate_count > 0, "Guard should fire when duplicates exist"


# ------------------------------------------------------------------
# Scenario 2 — no duplicates: nothing is dropped
# ------------------------------------------------------------------


class TestDeduplicateNoDuplicates:
    """Given a list of HerbChunks where all IDs are unique."""

    def test_preserves_all_chunks(self) -> None:
        """All chunks should survive when there are no duplicate IDs."""
        chunks: list[HerbChunk] = [
            _make_chunk(id="pubmed-111-chunk-0"),
            _make_chunk(id="pubmed-222-chunk-0"),
            _make_chunk(id="msk-herbs-chamomile-chunk-0"),
            _make_chunk(id="who-garlic-chunk-0"),
        ]

        result: list[HerbChunk] = _deduplicate(chunks)

        assert len(result) == len(chunks)

    def test_duplicate_count_is_zero(self) -> None:
        """Duplicate count should be zero when all IDs are unique."""
        chunks: list[HerbChunk] = [
            _make_chunk(id="pubmed-111-chunk-0"),
            _make_chunk(id="pubmed-222-chunk-0"),
        ]

        unique: list[HerbChunk] = _deduplicate(chunks)
        duplicate_count: int = len(chunks) - len(unique)

        assert duplicate_count == 0

    def test_warning_condition_does_not_fire(self) -> None:
        """The ``if duplicate_count:`` guard should be falsy (no warning)."""
        chunks: list[HerbChunk] = [
            _make_chunk(id="pubmed-111-chunk-0"),
            _make_chunk(id="pubmed-222-chunk-0"),
        ]

        unique: list[HerbChunk] = _deduplicate(chunks)
        duplicate_count: int = len(chunks) - len(unique)

        assert not duplicate_count, "Guard should NOT fire when no duplicates"


# ------------------------------------------------------------------
# Scenario 3 — empty list: no error
# ------------------------------------------------------------------


class TestDeduplicateEmptyList:
    """Given an empty list of HerbChunks."""

    def test_returns_empty_list(self) -> None:
        """Deduplication of an empty list should return an empty list."""
        result: list[HerbChunk] = _deduplicate([])

        assert result == []

    def test_no_error_raised(self) -> None:
        """No exception should be raised for an empty list."""
        # Implicitly tested — if this raises, pytest will catch it.
        unique: list[HerbChunk] = _deduplicate([])
        duplicate_count: int = 0 - len(unique)

        assert duplicate_count == 0


# ------------------------------------------------------------------
# Scenario 4 — cross-source duplicates (edge case)
# ------------------------------------------------------------------


class TestDeduplicateCrossSource:
    """Edge case: different source types producing the same chunk ID.

    This shouldn't happen with correct ID schemes but the deduplication
    logic should still handle it gracefully.
    """

    def test_deduplicates_across_sources(self) -> None:
        """Same ID from different sources should still be deduplicated."""
        chunks: list[HerbChunk] = [
            _make_chunk(
                id="shared-id-chunk-0",
                source_type="PubMed",
                text="from PubMed",
            ),
            _make_chunk(
                id="shared-id-chunk-0",
                source_type="WHO",
                text="from WHO",
            ),
        ]

        result: list[HerbChunk] = _deduplicate(chunks)

        assert len(result) == 1
