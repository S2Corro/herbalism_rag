# ---
# title: "Unit Test — GET /api/status"
# sprint: SPR-001
# task: T-006
# author: Developer Agent
# ---
"""Unit tests for the GET /api/status health-check endpoint.

These tests verify that the status route returns the correct HTTP status
code, content type, and response body without requiring a real Anthropic
API key or any external service.

Run with:
    pytest tests/test_status.py -v
"""

import os

# Set a fake API key BEFORE importing the app, so config validation passes.
# This must happen at module level before any backend imports.
os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_status_returns_200() -> None:
    """GET /api/status should return HTTP 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_status_body_contains_status_ok() -> None:
    """Response body must include {"status": "ok"}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
    body = response.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_status_body_contains_service_name() -> None:
    """Response body must include {"service": "herbalism-rag"}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
    body = response.json()
    assert body["service"] == "herbalism-rag"


@pytest.mark.asyncio
async def test_status_content_type_is_json() -> None:
    """Response Content-Type header must be application/json."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_status_body_contains_version() -> None:
    """Response body must include a version string."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
    body = response.json()
    assert "version" in body
    assert body["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_status_body_contains_doc_count() -> None:
    """Response body must include doc_count (0 during scaffold phase)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
    body = response.json()
    assert "doc_count" in body
    assert body["doc_count"] == 0
