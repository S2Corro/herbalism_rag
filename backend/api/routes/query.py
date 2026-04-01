"""Herbalism RAG — POST /api/query Controller.

Thin HTTP glue between FastAPI and the RAGPipeline service.  All business
logic lives in ``backend/rag/pipeline.py`` — this module only:

1. Receives and validates the ``QueryRequest`` via Pydantic (auto-422 on
   invalid input).
2. Pulls the shared ``RAGPipeline`` instance from ``app.state`` (wired by
   the lifespan in ``backend/main.py``).
3. Delegates to ``pipeline.run(question)``.
4. Maps pipeline exceptions to appropriate HTTP error codes.
5. Logs each request and response time via structlog.

Blueprints:
    BLU-001 §2, §5 — Controller layer contract
    BLU-002 §1, §5 — End-to-end flow, response schema
"""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from backend.api.schemas.requests import QueryRequest
from backend.api.schemas.responses import QueryResponse
from backend.rag.pipeline import (
    PipelineGeneratorError,
    PipelineRetrieverError,
    RAGPipeline,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

router: APIRouter = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Execute a RAG query",
    description=(
        "Accepts a natural-language question, retrieves the top-8 relevant "
        "herb chunks from ChromaDB, synthesizes an answer using Claude Haiku, "
        "and returns the answer with inline citations and source metadata."
    ),
)
async def post_query(
    body: QueryRequest,
    request: Request,
) -> QueryResponse:
    """Execute the RAG pipeline for a user question.

    Pulls the shared ``RAGPipeline`` from ``app.state``, delegates to
    ``pipeline.run()``, and maps typed pipeline errors to HTTP codes.

    Args:
        body: Validated ``QueryRequest`` containing the user's question.
        request: FastAPI ``Request`` used to access ``app.state.pipeline``.

    Returns:
        ``QueryResponse`` with answer, sources, and query_time_ms.

    Raises:
        HTTPException 503: If the retrieval stage (embeddings / ChromaDB) fails.
        HTTPException 502: If the generation stage (Anthropic API) fails.
        HTTPException 500: For any other unexpected pipeline failure.
    """
    start: float = time.monotonic()
    question: str = body.question

    logger.info("query_request_received", question=question[:100])

    pipeline: RAGPipeline = request.app.state.pipeline

    try:
        response: QueryResponse = await pipeline.run(question)
    except PipelineRetrieverError as exc:
        elapsed_ms: int = int((time.monotonic() - start) * 1000)
        logger.error(
            "query_retriever_error",
            question=question[:100],
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Retrieval service unavailable: {exc}",
        ) from exc
    except PipelineGeneratorError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "query_generator_error",
            question=question[:100],
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {exc}",
        ) from exc
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "query_unexpected_error",
            question=question[:100],
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected pipeline error — check server logs.",
        ) from exc

    elapsed_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "query_response_sent",
        question=question[:100],
        source_count=len(response.sources),
        elapsed_ms=elapsed_ms,
    )
    return response
