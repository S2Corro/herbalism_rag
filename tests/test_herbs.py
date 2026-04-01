# ---
# title: "Integration Tests — GET /api/herbs"
# sprint: SPR-005
# task: T-004
# author: Developer Agent A
# ---
"""Integration tests for the GET /api/herbs endpoint.

All tests use ``httpx.AsyncClient`` with ``ASGITransport`` against a
minimal FastAPI test app.  The ``HerbRepository`` is injected into
``app.state`` directly — no real ChromaDB is opened.

No real Anthropic API calls are made.

Run with:
    pytest tests/test_herbs.py -v
"""

import os

# MUST be set before any backend imports — config validation reads this env var.
os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.routes import herbs as herbs_router_module
from backend.db.herb_repository import HerbRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_app(repository: HerbRepository) -> FastAPI:
    """Create a minimal FastAPI test app with repository pre-set on app.state.

    State is set directly on the app object before any request, bypassing
    the need for a lifespan context manager.

    Args:
        repository: The mock ``HerbRepository`` to inject into ``app.state``.

    Returns:
        A configured ``FastAPI`` test instance with ``app.state.repository`` set.
    """
    test_app: FastAPI = FastAPI()
    test_app.include_router(herbs_router_module.router, prefix="/api")
    test_app.state.repository = repository
    return test_app


def _make_mock_repository(herbs: list[str] | None = None) -> MagicMock:
    """Build a mock HerbRepository with configurable list_herbs() output.

    Args:
        herbs: List of herb names to return from ``list_herbs()``.
            Defaults to a small sample set.

    Returns:
        A ``MagicMock`` spec'd to ``HerbRepository``.
    """
    mock: MagicMock = MagicMock(spec=HerbRepository)
    mock.list_herbs.return_value = (
        herbs if herbs is not None else ["Ashwagandha", "Chamomile", "Valerian"]
    )
    return mock


# ---------------------------------------------------------------------------
# Tests: happy path
# ---------------------------------------------------------------------------


class TestHerbsHappyPath:
    """Tests for successful GET /api/herbs responses."""

    @pytest.mark.asyncio
    async def test_returns_200(self) -> None:
        """GET /api/herbs should return HTTP 200."""
        app = _make_test_app(_make_mock_repository())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_body_has_herbs_key(self) -> None:
        """Response body must include a ``herbs`` key."""
        app = _make_test_app(_make_mock_repository())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert "herbs" in body

    @pytest.mark.asyncio
    async def test_response_body_herbs_is_list(self) -> None:
        """The ``herbs`` value must be a list."""
        app = _make_test_app(_make_mock_repository())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert isinstance(body["herbs"], list)

    @pytest.mark.asyncio
    async def test_response_body_has_count_key(self) -> None:
        """Response body must include a ``count`` key."""
        app = _make_test_app(_make_mock_repository())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert "count" in body

    @pytest.mark.asyncio
    async def test_count_matches_herbs_list_length(self) -> None:
        """The ``count`` value must equal the length of the ``herbs`` list."""
        herbs = ["Ashwagandha", "Chamomile", "Valerian"]
        app = _make_test_app(_make_mock_repository(herbs=herbs))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert body["count"] == len(herbs)
        assert body["count"] == len(body["herbs"])

    @pytest.mark.asyncio
    async def test_herb_names_are_returned_correctly(self) -> None:
        """The herb names returned should match the repository output."""
        herbs = ["Ashwagandha", "Chamomile", "Valerian"]
        app = _make_test_app(_make_mock_repository(herbs=herbs))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert body["herbs"] == herbs

    @pytest.mark.asyncio
    async def test_empty_collection_returns_empty_list(self) -> None:
        """Empty knowledge base must return ``{"herbs": [], "count": 0}``."""
        app = _make_test_app(_make_mock_repository(herbs=[]))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert body["herbs"] == []
        assert body["count"] == 0

    @pytest.mark.asyncio
    async def test_content_type_is_json(self) -> None:
        """Response Content-Type header must be application/json."""
        app = _make_test_app(_make_mock_repository())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_list_herbs_called_once(self) -> None:
        """The route must call ``repository.list_herbs()`` exactly once."""
        mock_repo = _make_mock_repository()
        app = _make_test_app(mock_repo)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.get("/api/herbs")

        mock_repo.list_herbs.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestHerbsErrorHandling:
    """Tests for repository error → HTTP error mapping."""

    @pytest.mark.asyncio
    async def test_runtime_error_returns_503(self) -> None:
        """A RuntimeError from the repository should map to HTTP 503."""
        mock_repo: MagicMock = MagicMock(spec=HerbRepository)
        mock_repo.list_herbs.side_effect = RuntimeError("ChromaDB unavailable")
        app = _make_test_app(mock_repo)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_500(self) -> None:
        """An unexpected exception from the repository should map to HTTP 500."""
        mock_repo: MagicMock = MagicMock(spec=HerbRepository)
        mock_repo.list_herbs.side_effect = Exception("Unexpected failure")
        app = _make_test_app(mock_repo)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_error_response_has_detail_field(self) -> None:
        """Error responses must include a ``detail`` field."""
        mock_repo: MagicMock = MagicMock(spec=HerbRepository)
        mock_repo.list_herbs.side_effect = RuntimeError("DB gone")
        app = _make_test_app(mock_repo)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/herbs")

        body = response.json()
        assert "detail" in body
        assert len(body["detail"]) > 0
