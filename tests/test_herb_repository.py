# ---
# title: "Unit Tests — HerbRepository"
# sprint: SPR-002
# task: T-005
# author: Developer Agent
# ---
"""Unit tests for the HerbRepository ChromaDB wrapper.

All tests use a temporary directory for ChromaDB storage — never the
real ``data/chroma_db/`` — and set a fake API key so no real Anthropic
calls are made.
"""

import os
import tempfile

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest

from backend.db.herb_repository import HerbRepository
from backend.models.herb_chunk import HerbChunk


@pytest.fixture()
def repo() -> HerbRepository:
    """Create a HerbRepository backed by a temporary directory."""
    tmpdir = tempfile.mkdtemp()
    return HerbRepository(chroma_db_path=tmpdir, collection_name="test")


def _make_chunks() -> list[HerbChunk]:
    """Create a set of test chunks from different sources."""
    return [
        HerbChunk(
            id="pubmed-1-chunk-0",
            text="Ashwagandha significantly reduced serum cortisol levels.",
            source_type="PubMed",
            title="Cortisol Study",
            url="https://pubmed.ncbi.nlm.nih.gov/1/",
            year="2020",
            herbs=["Ashwagandha"],
            chunk_index=0,
        ),
        HerbChunk(
            id="msk-2-chunk-0",
            text="Turmeric has anti-inflammatory properties.",
            source_type="MSK",
            title="Turmeric Monograph",
            url="https://msk.org/turmeric",
            year="2019",
            herbs=["Turmeric", "Curcumin"],
            chunk_index=0,
        ),
        HerbChunk(
            id="who-3-chunk-0",
            text="Ginger is used for nausea and digestive complaints.",
            source_type="WHO",
            title="WHO Ginger Monograph",
            url="https://who.int/ginger",
            year="2021",
            herbs=["Ginger"],
            chunk_index=0,
        ),
    ]


def test_add_and_search_round_trip(repo: HerbRepository) -> None:
    """Adding chunks then searching should return HerbChunk objects."""
    chunks = _make_chunks()
    repo.add(chunks)
    results = repo.search(query_embedding=[0.1] * 384, n=3)
    assert len(results) == 3
    assert all(isinstance(r, HerbChunk) for r in results)


def test_search_returns_correct_metadata(repo: HerbRepository) -> None:
    """Searched chunks should preserve their metadata through the round-trip."""
    chunks = _make_chunks()
    repo.add(chunks)
    results = repo.search(query_embedding=[0.1] * 384, n=3)
    ids_found = {r.id for r in results}
    assert "pubmed-1-chunk-0" in ids_found
    # Verify metadata survived
    pubmed_chunk = next(r for r in results if r.id == "pubmed-1-chunk-0")
    assert pubmed_chunk.source_type == "PubMed"
    assert pubmed_chunk.herbs == ["Ashwagandha"]


def test_stats_returns_correct_counts(repo: HerbRepository) -> None:
    """stats() should return correct doc_count and source breakdown."""
    repo.add(_make_chunks())
    s = repo.stats()
    assert s["doc_count"] == 3
    assert s["sources"] == {"PubMed": 1, "MSK": 1, "WHO": 1}


def test_list_herbs_sorted_and_deduplicated(repo: HerbRepository) -> None:
    """list_herbs() should return sorted, unique herb names."""
    repo.add(_make_chunks())
    herbs = repo.list_herbs()
    assert herbs == ["Ashwagandha", "Curcumin", "Ginger", "Turmeric"]


def test_add_upsert_no_duplicates(repo: HerbRepository) -> None:
    """Adding the same chunks twice should not create duplicates."""
    chunks = _make_chunks()
    repo.add(chunks)
    repo.add(chunks)
    assert repo.stats()["doc_count"] == 3


def test_search_empty_collection(repo: HerbRepository) -> None:
    """Searching an empty collection should return an empty list."""
    results = repo.search(query_embedding=[0.1] * 384, n=5)
    assert results == []


def test_add_empty_list(repo: HerbRepository) -> None:
    """Adding an empty list should return 0 and not error."""
    count = repo.add([])
    assert count == 0
    assert repo.stats()["doc_count"] == 0
