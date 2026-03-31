"""Herbalism RAG — API Response Schemas.

Pydantic models for all API response bodies. These schemas serve as both
runtime validation and auto-generated OpenAPI documentation.

- ``Source`` — a single citation source returned with each query answer.
- ``QueryResponse`` — the full RAG query response (answer + sources + timing).
- ``StatusResponse`` — the ``GET /api/status`` health-check response.
"""

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A single source citation returned with a RAG query answer.

    Each source corresponds to one ``HerbChunk`` that contributed to the
    generated answer.  The ``excerpt`` field contains the first 300
    characters of the chunk text for display in source cards.

    Attributes:
        source_type: Origin database (``"PubMed"``, ``"MSK"``,
            ``"USDA Duke"``, or ``"WHO"``).
        title: Document or article title.
        url: Direct link to the source document.
        year: Publication year (string — some sources lack year data).
        excerpt: First 300 characters of the source chunk text.
    """

    source_type: str = Field(..., description="Origin: PubMed | MSK | USDA Duke | WHO")
    title: str = Field(..., description="Document or article title")
    url: str = Field(..., description="Direct link to the source")
    year: str = Field(..., description="Publication year")
    excerpt: str = Field(..., description="First 300 chars of chunk text")


class QueryResponse(BaseModel):
    """Full response body for ``POST /api/query``.

    Contains the LLM-generated answer with inline citation markers
    (e.g. ``[1]``, ``[2]``), the list of source citations, and the
    total query processing time.

    Attributes:
        answer: LLM-generated answer with inline citation markers.
        sources: List of source citations referenced in the answer.
        query_time_ms: Total processing time in milliseconds.
    """

    answer: str = Field(..., description="LLM-generated answer with citations")
    sources: list[Source] = Field(
        default_factory=list, description="Source citations"
    )
    query_time_ms: int = Field(..., description="Total processing time in ms")


class StatusResponse(BaseModel):
    """Response body for ``GET /api/status`` health check.

    Attributes:
        status: Service status — ``"ok"`` when healthy.
        service: Service identifier — ``"herbalism-rag"``.
        version: Semantic version string (e.g. ``"0.1.0"``).
        doc_count: Number of chunks currently in the vector store.
    """

    status: str = Field(..., description="Service status: ok")
    service: str = Field(..., description="Service name: herbalism-rag")
    version: str = Field(..., description="Semantic version string")
    doc_count: int = Field(..., description="Chunk count in vector store")
