# ---
# title: "Unit Test — GET /api/status"
# sprint: SPR-001, SPR-005
# task: T-006 (original), T-003 (updated for lifespan wiring)
# author: Developer Agent
# updated: Developer Agent A (SPR-005 — patch lifespan deps)
# ---
"""Unit tests for the GET /api/status health-check endpoint.

These tests verify that the status route returns the correct HTTP status
code, content type, and response body without requiring a real Anthropic
API key or any external service.

In SPR-005, the lifespan was refactored to wire real services
(HerbRepository, RetrieverService, GeneratorService, RAGPipeline).
Those are patched here so tests remain fast and dependency-free.

The patches wrap the ``AsyncClient`` context manager — that is when
FastAPI triggers the lifespan and instantiates services.

Run with:
    pytest tests/test_status.py -v
"""

import os

# Set a fake API key BEFORE importing the app, so config validation passes.
# This must happen at module level before any backend imports.
os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


# ---------------------------------------------------------------------------
# Mock factory helpers
# ---------------------------------------------------------------------------


def _make_mock_repository() -> MagicMock:
    """Build a mock HerbRepository with collection.count() returning 0."""
    repo: MagicMock = MagicMock()
    repo.collection.count.return_value = 0
    repo.list_herbs.return_value = []
    return repo


def _make_mock_retriever() -> MagicMock:
    """Build a mock RetrieverService."""
    return MagicMock()


def _make_mock_generator() -> MagicMock:
    """Build a mock GeneratorService."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Shared context manager for patching all lifespan dependencies
# ---------------------------------------------------------------------------


def _patched_client() -> pytest.FixtureLookupError:
    """Not a fixture — use inline patch context managers in each test.

    Patches applied:
    - ``backend.main.HerbRepository`` — prevents ChromaDB disk access
    - ``backend.main.RetrieverService`` — prevents embedding model download
    - ``backend.main.GeneratorService`` — prevents Anthropic client creation

    Returns an ``AsyncClient`` ready for use in integration tests.
    """


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_returns_200() -> None:
    """GET /api/status should return HTTP 200."""
    with (
        patch("backend.main.HerbRepository", return_value=_make_mock_repository()),
        patch("backend.main.RetrieverService", return_value=_make_mock_retriever()),
        patch("backend.main.GeneratorService", return_value=_make_mock_generator()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_status_body_contains_status_ok() -> None:
    """Response body must include {"status": "ok"}."""
    with (
        patch("backend.main.HerbRepository", return_value=_make_mock_repository()),
        patch("backend.main.RetrieverService", return_value=_make_mock_retriever()),
        patch("backend.main.GeneratorService", return_value=_make_mock_generator()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/status")
    body = response.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_status_body_contains_service_name() -> None:
    """Response body must include {"service": "herbalism-rag"}."""
    with (
        patch("backend.main.HerbRepository", return_value=_make_mock_repository()),
        patch("backend.main.RetrieverService", return_value=_make_mock_retriever()),
        patch("backend.main.GeneratorService", return_value=_make_mock_generator()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/status")
    body = response.json()
    assert body["service"] == "herbalism-rag"


@pytest.mark.asyncio
async def test_status_content_type_is_json() -> None:
    """Response Content-Type header must be application/json."""
    with (
        patch("backend.main.HerbRepository", return_value=_make_mock_repository()),
        patch("backend.main.RetrieverService", return_value=_make_mock_retriever()),
        patch("backend.main.GeneratorService", return_value=_make_mock_generator()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/status")
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_status_body_contains_version() -> None:
    """Response body must include a version string."""
    with (
        patch("backend.main.HerbRepository", return_value=_make_mock_repository()),
        patch("backend.main.RetrieverService", return_value=_make_mock_retriever()),
        patch("backend.main.GeneratorService", return_value=_make_mock_generator()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/status")
    body = response.json()
    assert "version" in body
    assert body["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_status_body_contains_doc_count() -> None:
    """Response body must include doc_count (0 with empty mock collection)."""
    with (
        patch("backend.main.HerbRepository", return_value=_make_mock_repository()),
        patch("backend.main.RetrieverService", return_value=_make_mock_retriever()),
        patch("backend.main.GeneratorService", return_value=_make_mock_generator()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/status")
    body = response.json()
    assert "doc_count" in body
    assert body["doc_count"] == 0
