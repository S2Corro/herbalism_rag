"""Herbalism RAG — RAGPipeline Orchestrator.

Coordinates the full retrieval-augmented generation flow:

1. **Retrieve** — ``RetrieverService.search()`` embeds the question and
   pulls the top-*n* ``HerbChunk`` objects from ChromaDB.
2. **Generate** — ``GeneratorService.synthesize()`` sends the question
   and chunks to Claude Haiku, which produces an answer with inline
   ``[N]`` citation markers.
3. **Package** — Builds a ``QueryResponse`` with the answer text,
   source metadata, and total pipeline timing.

This is the single entry point called by the Controller Layer
(BLU-001 §5) — the controller calls ``pipeline.run(question)`` and
returns the ``QueryResponse`` directly.

Blueprints:
    BLU-001 §5 — Service-layer contract
    BLU-002 §1 — End-to-end RAG flow
"""

from __future__ import annotations

import time

import structlog

from backend.api.schemas.responses import QueryResponse, Source
from backend.models.herb_chunk import HerbChunk
from backend.rag.generator import GeneratorService, GeneratorAPIError
from backend.rag.retriever import RetrieverService, EmbeddingModelError

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class PipelineError(Exception):
    """Raised when a stage of the RAG pipeline fails."""


class PipelineRetrieverError(PipelineError):
    """Raised when the retrieval stage fails."""


class PipelineGeneratorError(PipelineError):
    """Raised when the generation stage fails."""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class RAGPipeline:
    """Orchestrates the retrieve → generate → respond flow.

    Args:
        retriever: Service for embedding and vector search.
        generator: Service for LLM synthesis.
    """

    def __init__(
        self,
        retriever: RetrieverService,
        generator: GeneratorService,
    ) -> None:
        """Initialize with retriever and generator services.

        Args:
            retriever: The ``RetrieverService`` instance.
            generator: The ``GeneratorService`` instance.
        """
        self._retriever: RetrieverService = retriever
        self._generator: GeneratorService = generator

    async def run(self, question: str) -> QueryResponse:
        """Execute the full RAG pipeline.

        Flow: embed → search → synthesize → respond.

        Args:
            question: The user's natural-language question.

        Returns:
            A ``QueryResponse`` with answer, sources, and timing.

        Raises:
            PipelineRetrieverError: If retrieval fails.
            PipelineGeneratorError: If generation fails.
        """
        start: float = time.monotonic()

        # 1. Retrieve
        chunks: list[HerbChunk] = self._retrieve(question)

        # 2. Generate
        answer: str = await self._generate(question, chunks)

        # 3. Package
        elapsed_ms: int = int((time.monotonic() - start) * 1000)
        sources: list[Source] = [
            Source(**chunk.to_source()) for chunk in chunks
        ]

        response: QueryResponse = QueryResponse(
            answer=answer,
            sources=sources,
            query_time_ms=elapsed_ms,
        )

        logger.info(
            "pipeline_run",
            question=question[:100],
            chunk_count=len(chunks),
            query_time_ms=elapsed_ms,
        )
        return response

    def _retrieve(self, question: str) -> list[HerbChunk]:
        """Run the retrieval stage with error wrapping.

        Args:
            question: The user's question.

        Returns:
            List of retrieved ``HerbChunk`` objects.

        Raises:
            PipelineRetrieverError: If retrieval fails.
        """
        try:
            return self._retriever.search(question)
        except (EmbeddingModelError, RuntimeError) as exc:
            raise PipelineRetrieverError(
                f"Retrieval failed for question: {exc}"
            ) from exc

    async def _generate(
        self,
        question: str,
        chunks: list[HerbChunk],
    ) -> str:
        """Run the generation stage with error wrapping.

        Args:
            question: The user's question.
            chunks: Retrieved chunks to synthesize from.

        Returns:
            The Claude-generated answer text.

        Raises:
            PipelineGeneratorError: If generation fails.
        """
        try:
            return await self._generator.synthesize(question, chunks)
        except GeneratorAPIError as exc:
            raise PipelineGeneratorError(
                f"Generation failed for question: {exc}"
            ) from exc
