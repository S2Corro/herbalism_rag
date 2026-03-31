# ---
# title: "Unit Tests — RAGPipeline"
# sprint: SPR-004
# task: T-004
# author: Developer Agent B
# ---
"""Unit tests for the RAGPipeline orchestrator.

Both retriever and generator are mocked — no real embeddings or
API calls. Tests verify the end-to-end flow, QueryResponse structure,
timing, and error propagation.
"""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas.responses import QueryResponse, Source
from backend.models.herb_chunk import HerbChunk
from backend.rag.generator import GeneratorAPIError, GeneratorService
from backend.rag.pipeline import (
    PipelineGeneratorError,
    PipelineRetrieverError,
    RAGPipeline,
)
from backend.rag.retriever import EmbeddingModelError, RetrieverService

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _make_chunks() -> list[HerbChunk]:
    """Create test HerbChunks."""
    return [
        HerbChunk(
            id="pubmed-1-chunk-0",
            text="Ashwagandha reduced cortisol levels in a randomized trial.",
            source_type="PubMed",
            title="Cortisol Study",
            url="https://pubmed.ncbi.nlm.nih.gov/1/",
            year="2020",
            herbs=["Ashwagandha"],
            chunk_index=0,
        ),
    ]


def _make_mock_retriever(
    chunks: list[HerbChunk] | None = None,
    error: Exception | None = None,
) -> MagicMock:
    """Build a mock RetrieverService."""
    mock: MagicMock = MagicMock(spec=RetrieverService)
    if error:
        mock.search.side_effect = error
    else:
        mock.search.return_value = chunks if chunks is not None else []
    return mock


def _make_mock_generator(
    answer: str = "Test answer [1].",
    error: Exception | None = None,
) -> MagicMock:
    """Build a mock GeneratorService."""
    mock: MagicMock = MagicMock(spec=GeneratorService)
    if error:
        mock.synthesize = AsyncMock(side_effect=error)
    else:
        mock.synthesize = AsyncMock(return_value=answer)
    return mock


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------


class TestPipelineRun:
    """Tests for the pipeline.run() orchestrator."""

    @pytest.mark.asyncio
    async def test_run_returns_query_response(self) -> None:
        """run() should return a QueryResponse with correct structure."""
        chunks: list[HerbChunk] = _make_chunks()
        retriever = _make_mock_retriever(chunks=chunks)
        generator = _make_mock_generator(answer="Ashwagandha helps [1].")

        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        response: QueryResponse = await pipeline.run("What helps cortisol?")

        assert isinstance(response, QueryResponse)
        assert response.answer == "Ashwagandha helps [1]."
        assert len(response.sources) == 1
        assert isinstance(response.sources[0], Source)

    @pytest.mark.asyncio
    async def test_run_sources_contain_correct_metadata(self) -> None:
        """Sources in the response should match the chunk metadata."""
        chunks: list[HerbChunk] = _make_chunks()
        retriever = _make_mock_retriever(chunks=chunks)
        generator = _make_mock_generator()

        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        response: QueryResponse = await pipeline.run("test")

        src: Source = response.sources[0]
        assert src.source_type == "PubMed"
        assert src.title == "Cortisol Study"
        assert src.url == "https://pubmed.ncbi.nlm.nih.gov/1/"
        assert src.year == "2020"

    @pytest.mark.asyncio
    async def test_query_time_ms_is_positive_int(self) -> None:
        """query_time_ms should be a non-negative integer."""
        retriever = _make_mock_retriever(chunks=_make_chunks())
        generator = _make_mock_generator()

        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        response: QueryResponse = await pipeline.run("test")

        assert isinstance(response.query_time_ms, int)
        assert response.query_time_ms >= 0

    @pytest.mark.asyncio
    async def test_run_with_empty_results(self) -> None:
        """run() should work when retriever returns no chunks."""
        retriever = _make_mock_retriever(chunks=[])
        generator = _make_mock_generator(answer="No relevant sources found.")

        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        response: QueryResponse = await pipeline.run("unknown topic")

        assert response.sources == []
        assert isinstance(response.answer, str)

    @pytest.mark.asyncio
    async def test_retriever_calls_search_with_question(self) -> None:
        """The retriever should receive the user's question."""
        retriever = _make_mock_retriever(chunks=[])
        generator = _make_mock_generator()

        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        await pipeline.run("ashwagandha benefits")

        retriever.search.assert_called_once_with("ashwagandha benefits")

    @pytest.mark.asyncio
    async def test_generator_receives_question_and_chunks(self) -> None:
        """The generator should receive both question and chunks."""
        chunks: list[HerbChunk] = _make_chunks()
        retriever = _make_mock_retriever(chunks=chunks)
        generator = _make_mock_generator()

        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        await pipeline.run("cortisol question")

        generator.synthesize.assert_called_once_with("cortisol question", chunks)


class TestPipelineErrors:
    """Tests for pipeline error handling."""

    @pytest.mark.asyncio
    async def test_retriever_failure_raises_pipeline_retriever_error(
        self,
    ) -> None:
        """Retriever errors should be wrapped as PipelineRetrieverError."""
        retriever = _make_mock_retriever(
            error=EmbeddingModelError("model crashed"),
        )
        generator = _make_mock_generator()

        pipeline = RAGPipeline(retriever=retriever, generator=generator)

        with pytest.raises(PipelineRetrieverError):
            await pipeline.run("test")

    @pytest.mark.asyncio
    async def test_generator_failure_raises_pipeline_generator_error(
        self,
    ) -> None:
        """Generator errors should be wrapped as PipelineGeneratorError."""
        retriever = _make_mock_retriever(chunks=_make_chunks())
        generator = _make_mock_generator(
            error=GeneratorAPIError("API down"),
        )

        pipeline = RAGPipeline(retriever=retriever, generator=generator)

        with pytest.raises(PipelineGeneratorError):
            await pipeline.run("test")
