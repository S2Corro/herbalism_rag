# ---
# title: "Unit Tests — RetrieverService"
# sprint: SPR-004
# task: T-004
# author: Developer Agent B
# ---
"""Unit tests for the RetrieverService.

Uses the real ``sentence-transformers`` model (local, no API cost)
with a temporary ChromaDB directory so tests are isolated.
"""

import os
import tempfile

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest

from backend.db.herb_repository import HerbRepository
from backend.models.herb_chunk import HerbChunk
from backend.rag.retriever import EmbeddingModelError, RetrieverService


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture()
def repo() -> HerbRepository:
    """Create a HerbRepository backed by a temp directory."""
    tmpdir: str = tempfile.mkdtemp()
    return HerbRepository(chroma_db_path=tmpdir, collection_name="test_ret")


@pytest.fixture()
def populated_repo(repo: HerbRepository) -> HerbRepository:
    """Repository pre-populated with test chunks via direct collection insert.

    Bypasses ``repo.add()`` because ChromaDB 0.5.23 requires explicit
    embeddings when ``embedding_function=None`` is set on the collection.
    """
    chunks: list[HerbChunk] = [
        HerbChunk(
            id="pubmed-1-chunk-0",
            text="Ashwagandha significantly reduced serum cortisol levels in a randomized trial.",
            source_type="PubMed",
            title="Cortisol Study",
            url="https://pubmed.ncbi.nlm.nih.gov/1/",
            year="2020",
            herbs=["Ashwagandha"],
            chunk_index=0,
        ),
        HerbChunk(
            id="msk-2-chunk-0",
            text="Turmeric curcumin has demonstrated anti-inflammatory properties.",
            source_type="MSK",
            title="Turmeric Monograph",
            url="https://msk.org/turmeric",
            year="2019",
            herbs=["Turmeric"],
            chunk_index=0,
        ),
    ]
    # Insert directly with dummy 384-d embeddings (ChromaDB needs them
    # when no embedding_function is configured on the collection)
    repo.collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[c.to_chroma_metadata() for c in chunks],
        embeddings=[[0.1] * 384 for _ in chunks],
    )
    return repo


@pytest.fixture()
def retriever(populated_repo: HerbRepository) -> RetrieverService:
    """RetrieverService with a populated repo."""
    return RetrieverService(repository=populated_repo)


@pytest.fixture()
def empty_retriever(repo: HerbRepository) -> RetrieverService:
    """RetrieverService with an empty repo."""
    return RetrieverService(repository=repo)


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------


def test_embed_returns_384_floats(retriever: RetrieverService) -> None:
    """embed() should return a list of exactly 384 floats."""
    vector: list[float] = retriever.embed("test input text")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(v, float) for v in vector)


def test_embed_different_texts_produce_different_vectors(
    retriever: RetrieverService,
) -> None:
    """Different inputs should produce different embedding vectors."""
    v1: list[float] = retriever.embed("ashwagandha cortisol")
    v2: list[float] = retriever.embed("unrelated topic like weather")
    assert v1 != v2


def test_search_returns_herb_chunks(retriever: RetrieverService) -> None:
    """search() on a populated repo should return HerbChunk objects."""
    results: list[HerbChunk] = retriever.search("cortisol", n=2)
    assert len(results) > 0
    assert all(isinstance(r, HerbChunk) for r in results)


def test_search_respects_n_limit(retriever: RetrieverService) -> None:
    """search() should return at most n results."""
    results: list[HerbChunk] = retriever.search("herbs", n=1)
    assert len(results) <= 1


def test_search_empty_repo_returns_empty_list(
    empty_retriever: RetrieverService,
) -> None:
    """search() on an empty repo should return an empty list."""
    results: list[HerbChunk] = empty_retriever.search("anything")
    assert results == []
