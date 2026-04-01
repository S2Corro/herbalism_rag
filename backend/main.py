"""Herbalism RAG — FastAPI Application Factory.

This module creates and configures the FastAPI application instance.
It follows the app-factory pattern:

1. Validates configuration on import (fails fast if ANTHROPIC_API_KEY is
   missing).
2. Wires up the full service graph in the lifespan context manager:
   - ``HerbRepository`` (ChromaDB — repository layer)
   - ``RetrieverService`` (embeddings — service layer)
   - ``GeneratorService`` (Anthropic Claude — service layer)
   - ``RAGPipeline`` (orchestrator — service layer)
   All are stored on ``app.state`` for injection into route handlers.
3. Mounts the ``/api`` routes: ``/query``, ``/herbs``, and ``/status``.
4. Mounts the ``frontend/`` directory as static files at ``/`` (catch-all,
   must come LAST).
5. Adds CORS middleware (permissive for development; Phase 7 tightens this).
6. Emits structured JSON log lines on startup and shutdown (GOV-006).

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

from backend.api.routes import herbs as herbs_router_module
from backend.api.routes import query as query_router_module
from backend.api.schemas.responses import StatusResponse
from backend.config import settings  # noqa: F401 — fail fast on missing key
from backend.db.herb_repository import HerbRepository
from backend.rag.generator import GeneratorService
from backend.rag.pipeline import RAGPipeline
from backend.rag.retriever import RetrieverService

# ---------------------------------------------------------------------------
# Structured logging setup (GOV-006)
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
# Lifespan — startup / shutdown + dependency wiring
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Wire the service graph on startup; tear down on shutdown.

    Constructs the full dependency chain in one place so all routes share
    the same singletons via ``app.state``.  This avoids per-request
    model loading (expensive) and ChromaDB client churn.

    Startup order:
        1. ``HerbRepository`` — opens ChromaDB persistent client
        2. ``RetrieverService`` — loads sentence-transformers model
        3. ``GeneratorService`` — creates Anthropic async client
        4. ``RAGPipeline`` — wires retriever + generator together

    Args:
        app: The FastAPI application instance.
    """
    # 1. Repository
    repository: HerbRepository = HerbRepository(
        chroma_db_path=settings.chroma_db_path,
        collection_name=settings.collection_name,
    )
    app.state.repository = repository

    # 2. Retriever
    retriever: RetrieverService = RetrieverService(
        repository=repository,
        model_name=settings.embedding_model,
    )
    app.state.retriever = retriever

    # 3. Generator
    generator: GeneratorService = GeneratorService(
        api_key=settings.anthropic_api_key,
        model=settings.llm_model,
    )
    app.state.generator = generator

    # 4. Pipeline
    pipeline: RAGPipeline = RAGPipeline(
        retriever=retriever,
        generator=generator,
    )
    app.state.pipeline = pipeline

    doc_count: int = repository.collection.count()
    logger.info(
        "startup",
        status="ok",
        service=_SERVICE_NAME,
        version=_VERSION,
        doc_count=doc_count,
    )

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
app.include_router(query_router_module.router, prefix="/api", tags=["query"])
app.include_router(herbs_router_module.router, prefix="/api", tags=["herbs"])


from fastapi import Request  # noqa: E402 — import after router includes


@app.get("/api/status", response_model=StatusResponse, tags=["status"])
async def get_status(request: Request) -> StatusResponse:
    """Return application health status with real ChromaDB doc count.

    Reads the live document count from the shared ``HerbRepository`` stored
    in ``app.state``.  Returns 0 if the collection is empty (e.g. knowledge
    base not yet populated).

    Args:
        request: FastAPI ``Request`` used to access ``app.state.repository``.

    Returns:
        ``StatusResponse`` with status, service name, version, and doc_count.
    """
    try:
        doc_count: int = request.app.state.repository.collection.count()
    except Exception:
        doc_count = 0

    return StatusResponse(
        status="ok",
        service=_SERVICE_NAME,
        version=_VERSION,
        doc_count=doc_count,
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
