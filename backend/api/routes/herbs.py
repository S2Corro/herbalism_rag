"""Herbalism RAG — GET /api/herbs Controller.

Thin HTTP glue exposing the list of indexed herb names from ChromaDB.
All storage logic lives in ``HerbRepository.list_herbs()`` — this module
only handles HTTP and logging.

Blueprints:
    BLU-001 §2, §5 — Controller layer contract
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from backend.db.herb_repository import HerbRepository

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

router: APIRouter = APIRouter()


# ---------------------------------------------------------------------------
# Response model (inline — simple enough not to warrant a schema file)
# ---------------------------------------------------------------------------


class HerbListResponse:
    """Typed wrapper returned by list_herbs.

    Not a Pydantic model by design — FastAPI will serialize the plain dict
    returned by ``list_herbs`` directly; this class documents the shape.
    """


@router.get(
    "/herbs",
    summary="List indexed herb names",
    description=(
        "Returns a sorted, deduplicated list of all herb names currently "
        "available in the ChromaDB vector store.  Returns an empty list "
        "if the knowledge base has not yet been populated."
    ),
)
async def list_herbs(request: Request) -> dict[str, list[str] | int]:
    """Return a sorted list of unique herb names from the vector store.

    Pulls the shared ``HerbRepository`` from ``app.state`` and delegates
    to ``list_herbs()``.  Maps repository failures to HTTP 503.

    Args:
        request: FastAPI ``Request`` used to access ``app.state.repository``.

    Returns:
        JSON object ``{"herbs": [...], "count": N}`` where ``herbs`` is a
        sorted, deduplicated list of herb names.

    Raises:
        HTTPException 503: If the ChromaDB repository call fails.
    """
    logger.info("herbs_request_received")

    repository: HerbRepository = request.app.state.repository

    try:
        herbs: list[str] = repository.list_herbs()
    except RuntimeError as exc:
        logger.error("herbs_repository_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Repository unavailable: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("herbs_unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error listing herbs — check server logs.",
        ) from exc

    logger.info("herbs_response_sent", count=len(herbs))
    return {"herbs": herbs, "count": len(herbs)}
