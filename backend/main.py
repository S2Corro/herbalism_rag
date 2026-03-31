"""Herbalism RAG — FastAPI Application Factory.

This module creates and configures the FastAPI application instance.
It follows the app-factory pattern:

1. Validates configuration on import (fails fast if ANTHROPIC_API_KEY is missing).
2. Mounts the ``frontend/`` directory as static files at ``/``.
3. Registers the ``/api`` router (currently just the status health-check).
4. Adds CORS middleware (permissive for development; production tightening
   is planned for Phase 7).
5. Emits a structured JSON log line on startup.

Run with:
    uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.schemas.responses import StatusResponse

from backend.config import settings  # noqa: F401 — fail fast on missing key


# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SERVICE_NAME: str = "herbalism-rag"
_VERSION: str = "0.1.0"
_FRONTEND_DIR: Path = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events.

    On startup, emits a structured JSON log line with service metadata
    as required by GOV-006. On shutdown, emits a clean shutdown message.

    Args:
        app: The FastAPI application instance.
    """
    logger.info("startup", status="ok", service=_SERVICE_NAME, doc_count=0)
    yield
    logger.info("shutdown", status="ok", service=_SERVICE_NAME)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app: FastAPI = FastAPI(
    title="Herbalism RAG",
    description="Evidence-based herbal medicine answers with source citations.",
    version=_VERSION,
    lifespan=lifespan,
)

# CORS — permissive for local development (Phase 7 will tighten this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/api/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Return application health status.

    Returns a JSON object with the service name, version, operational
    status, and the current document count in the vector store (0 until
    ingesters are implemented in a later phase).

    Returns:
        StatusResponse with status, service name, version, and doc_count.
    """
    return StatusResponse(
        status="ok",
        service=_SERVICE_NAME,
        version=_VERSION,
        doc_count=0,
    )


# ---------------------------------------------------------------------------
# Static file mounting (must be LAST — it's a catch-all)
# ---------------------------------------------------------------------------
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_DIR), html=True),
        name="frontend",
    )
