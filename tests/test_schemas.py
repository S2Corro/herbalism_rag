# ---
# title: "Unit Tests — API Schemas"
# sprint: SPR-002
# task: T-005
# author: Developer Agent
# ---
"""Unit tests for request and response Pydantic schemas.

Tests cover Source, QueryResponse, StatusResponse serialization
and QueryRequest validation (valid, empty, whitespace, too-long).
"""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest
from pydantic import ValidationError

from backend.api.schemas.requests import QueryRequest
from backend.api.schemas.responses import QueryResponse, Source, StatusResponse


def test_source_serializes_correctly() -> None:
    """Source model should serialize all fields."""
    src = Source(
        source_type="PubMed",
        title="Test Study",
        url="https://example.com",
        year="2024",
        excerpt="Some excerpt text",
    )
    data = src.model_dump()
    assert data["source_type"] == "PubMed"
    assert data["excerpt"] == "Some excerpt text"


def test_query_response_with_sources() -> None:
    """QueryResponse should serialize with a list of sources."""
    resp = QueryResponse(
        answer="Ashwagandha helps [1].",
        sources=[
            Source(source_type="PubMed", title="S1", url="u1", year="2024", excerpt="e1"),
        ],
        query_time_ms=1200,
    )
    data = resp.model_dump()
    assert len(data["sources"]) == 1
    assert data["query_time_ms"] == 1200


def test_status_response_serializes() -> None:
    """StatusResponse should match the /api/status contract."""
    resp = StatusResponse(
        status="ok",
        service="herbalism-rag",
        version="0.1.0",
        doc_count=42,
    )
    data = resp.model_dump()
    assert data["status"] == "ok"
    assert data["doc_count"] == 42


def test_query_request_valid() -> None:
    """Valid question should pass validation."""
    req = QueryRequest(question="What helps with stress?")
    assert req.question == "What helps with stress?"


def test_query_request_strips_whitespace() -> None:
    """QueryRequest should strip leading/trailing whitespace."""
    req = QueryRequest(question="  padded question  ")
    assert req.question == "padded question"


def test_query_request_empty_string_rejected() -> None:
    """Empty string should raise ValidationError."""
    with pytest.raises(ValidationError):
        QueryRequest(question="")


def test_query_request_whitespace_only_rejected() -> None:
    """Whitespace-only string should raise ValidationError."""
    with pytest.raises(ValidationError):
        QueryRequest(question="   ")


def test_query_request_too_long_rejected() -> None:
    """Question exceeding 1000 chars should raise ValidationError."""
    with pytest.raises(ValidationError):
        QueryRequest(question="x" * 1001)
