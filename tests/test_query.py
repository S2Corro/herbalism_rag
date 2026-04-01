# ---
# title: "Integration Tests — POST /api/query"
# sprint: SPR-005
# task: T-004
# author: Developer Agent A
# ---
"""Integration tests for the POST /api/query endpoint.

All tests use ``httpx.AsyncClient`` with ``ASGITransport`` against a
minimal FastAPI test app.  The ``RAGPipeline`` is injected into
``app.state`` directly — no real ChromaDB or embedding model is loaded.

No real Anthropic API calls are made.

Run with:
    pytest tests/test_query.py -v
"""

import os

# MUST be set before any backend imports — config validation reads this env var.
os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.routes import query as query_router_module
from backend.api.schemas.responses import QueryResponse, Source
from backend.rag.pipeline import (
    PipelineGeneratorError,
    PipelineRetrieverError,
    RAGPipeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_query_response(
    answer: str = "Ashwagandha reduces cortisol [1].",
    sources: list[Source] | None = None,
    query_time_ms: int = 42,
) -> QueryResponse:
    """Build a minimal QueryResponse for use in mock return values."""
    if sources is None:
        sources = [
            Source(
                source_type="PubMed",
                title="Cortisol Study",
                url="https://pubmed.ncbi.nlm.nih.gov/1/",
                year="2020",
                excerpt="Ashwagandha significantly reduced serum cortisol levels.",
            )
        ]
    return QueryResponse(answer=answer, sources=sources, query_time_ms=query_time_ms)


def _make_test_app(pipeline: RAGPipeline) -> FastAPI:
    """Create a minimal FastAPI test app with pipeline pre-set on app.state.

    State is set directly on the app object before any request, bypassing
    the need for a lifespan context manager.

    Args:
        pipeline: The mock ``RAGPipeline`` to inject into ``app.state``.

    Returns:
        A configured ``FastAPI`` test instance with ``app.state.pipeline`` set.
    """
    test_app: FastAPI = FastAPI()
    test_app.include_router(query_router_module.router, prefix="/api")
    test_app.state.pipeline = pipeline
    return test_app


# ---------------------------------------------------------------------------
# Tests: happy path
# ---------------------------------------------------------------------------


class TestQueryHappyPath:
    """Tests for successful POST /api/query responses."""

    @pytest.mark.asyncio
    async def test_valid_question_returns_200(self) -> None:
        """A valid question should return HTTP 200."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(return_value=_make_query_response())
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "What helps with cortisol?"}
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_body_has_answer(self) -> None:
        """Response body must include an ``answer`` string."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(
            return_value=_make_query_response(answer="Ashwagandha helps [1].")
        )
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "Cortisol?"}
            )

        body = response.json()
        assert "answer" in body
        assert body["answer"] == "Ashwagandha helps [1]."

    @pytest.mark.asyncio
    async def test_response_body_has_sources_list(self) -> None:
        """Response body must include a ``sources`` list."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(return_value=_make_query_response())
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "Herbs for stress?"}
            )

        body = response.json()
        assert "sources" in body
        assert isinstance(body["sources"], list)
        assert len(body["sources"]) == 1

    @pytest.mark.asyncio
    async def test_response_body_has_query_time_ms(self) -> None:
        """Response body must include a non-negative ``query_time_ms`` int."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(return_value=_make_query_response())
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "Adaptogens?"}
            )

        body = response.json()
        assert "query_time_ms" in body
        assert isinstance(body["query_time_ms"], int)
        assert body["query_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_source_metadata_fields_present(self) -> None:
        """Each source must have source_type, title, url, year, excerpt."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(return_value=_make_query_response())
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "Adaptogens for stress?"}
            )

        source = response.json()["sources"][0]
        assert source["source_type"] == "PubMed"
        assert source["title"] == "Cortisol Study"
        assert "url" in source
        assert "year" in source
        assert "excerpt" in source

    @pytest.mark.asyncio
    async def test_pipeline_run_called_with_question(self) -> None:
        """The route must pass the exact question string to pipeline.run()."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(return_value=_make_query_response())
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/query", json={"question": "Holy basil benefits?"}
            )

        mock_pipeline.run.assert_called_once_with("Holy basil benefits?")

    @pytest.mark.asyncio
    async def test_empty_sources_list_is_valid(self) -> None:
        """A response with no sources (empty knowledge base) is still HTTP 200."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(
            return_value=_make_query_response(
                answer="No relevant sources found.", sources=[]
            )
        )
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "Unknown topic xyz123?"}
            )

        assert response.status_code == 200
        assert response.json()["sources"] == []


# ---------------------------------------------------------------------------
# Tests: validation errors (auto-422 via Pydantic)
# ---------------------------------------------------------------------------


class TestQueryValidation:
    """Tests for request body validation (auto-422 responses)."""

    @pytest.mark.asyncio
    async def test_missing_question_returns_422(self) -> None:
        """A request body with no ``question`` field should return 422."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/query", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_blank_question_returns_422(self) -> None:
        """A whitespace-only question should return 422 (validator rejects it)."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "   "}
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_question_too_long_returns_422(self) -> None:
        """A question exceeding 1000 characters should return 422."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "x" * 1001}
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_question_too_short_returns_422(self) -> None:
        """A question under 3 characters should return 422."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "hi"}
            )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestQueryErrorHandling:
    """Tests for pipeline error → HTTP error mapping."""

    @pytest.mark.asyncio
    async def test_retriever_error_returns_503(self) -> None:
        """A PipelineRetrieverError should map to HTTP 503."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(
            side_effect=PipelineRetrieverError("Embeddings model crashed")
        )
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "What is chamomile?"}
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_generator_error_returns_502(self) -> None:
        """A PipelineGeneratorError should map to HTTP 502."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(
            side_effect=PipelineGeneratorError("Anthropic API down")
        )
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "What is chamomile?"}
            )

        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_500(self) -> None:
        """Any other exception should map to HTTP 500."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(side_effect=RuntimeError("Unexpected crash"))
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "What is chamomile?"}
            )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_error_response_has_detail_field(self) -> None:
        """Error responses (5xx) must include a ``detail`` field."""
        mock_pipeline: MagicMock = MagicMock(spec=RAGPipeline)
        mock_pipeline.run = AsyncMock(
            side_effect=PipelineRetrieverError("ChromaDB unavailable")
        )
        app = _make_test_app(mock_pipeline)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/query", json={"question": "What is chamomile?"}
            )

        body = response.json()
        assert "detail" in body
        assert len(body["detail"]) > 0
