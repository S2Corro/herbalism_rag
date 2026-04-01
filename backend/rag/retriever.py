"""Herbalism RAG — RetrieverService.

Handles the embedding and retrieval stages of the RAG pipeline:

1. **Embed** — uses ``sentence-transformers/all-MiniLM-L6-v2`` to convert
   a text string into a 384-dimensional vector on the local CPU (no API
   cost, no privacy leak).
2. **Search** — passes the vector to ``HerbRepository.search()`` and
   returns the top-*n* ``HerbChunk`` objects ranked by cosine similarity.

This service sits in the **Service Layer** (BLU-001 §2) and delegates all
ChromaDB contact to the Repository Layer.

Blueprints:
    BLU-002 §2 — Embedding specification
    BLU-002 §3 — Retrieval specification
"""

from __future__ import annotations

import time

import structlog
from sentence_transformers import SentenceTransformer

from backend.db.herb_repository import HerbRepository
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class EmbeddingModelError(Exception):
    """Raised when the sentence-transformers model fails to load."""


class RetrieverService:
    """Service that embeds text and retrieves similar HerbChunks.

    Uses ``sentence-transformers/all-MiniLM-L6-v2`` for local CPU
    embeddings (384-d) and delegates vector search to ``HerbRepository``.

    Args:
        repository: The ``HerbRepository`` used for vector search.
        model_name: HuggingFace model identifier for embeddings.

    Raises:
        EmbeddingModelError: If the embedding model cannot be loaded.
    """

    def __init__(
        self,
        repository: HerbRepository,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        """Initialize with a HerbRepository and load the embedding model.

        Args:
            repository: The repository for ChromaDB operations.
            model_name: HuggingFace model identifier.

        Raises:
            EmbeddingModelError: If the model cannot be loaded.
        """
        self._repository: HerbRepository = repository
        self._model_name: str = model_name

        start: float = time.monotonic()
        try:
            self._model: SentenceTransformer = SentenceTransformer(model_name)
        except Exception as exc:
            raise EmbeddingModelError(
                f"Failed to load embedding model '{model_name}': {exc}"
            ) from exc

        elapsed_ms: int = int((time.monotonic() - start) * 1000)
        logger.info(
            "retriever_model_loaded",
            model=model_name,
            elapsed_ms=elapsed_ms,
        )

    def embed(self, text: str) -> list[float]:
        """Embed a text string into a 384-dimensional vector.

        Args:
            text: The input text to embed.

        Returns:
            A list of 384 floats representing the embedding vector.

        Raises:
            EmbeddingModelError: If encoding fails.
        """
        start: float = time.monotonic()
        try:
            vector: list[float] = self._model.encode(  # type: ignore[assignment]
                text, convert_to_numpy=True
            ).tolist()
        except Exception as exc:
            raise EmbeddingModelError(
                f"Failed to embed text: {exc}"
            ) from exc

        elapsed_ms: int = int((time.monotonic() - start) * 1000)
        logger.info(
            "retriever_embed",
            text_length=len(text),
            vector_dim=len(vector),
            elapsed_ms=elapsed_ms,
        )
        return vector

    def search(self, question: str, n: int = 8) -> list[HerbChunk]:
        """Embed the question and search ChromaDB for similar chunks.

        Calls ``self.embed(question)`` to produce a query vector, then
        delegates to ``self._repository.search(embedding, n)`` for
        cosine-similarity retrieval.

        Args:
            question: The user's natural-language question.
            n: Maximum number of chunks to return.

        Returns:
            List of ``HerbChunk`` objects ordered by similarity.
            Empty list if no results or collection is empty.

        Raises:
            EmbeddingModelError: If embedding the question fails.
            RuntimeError: If the repository search fails.
        """
        start: float = time.monotonic()

        embedding: list[float] = self.embed(question)
        chunks: list[HerbChunk] = self._repository.search(
            query_embedding=embedding, n=n,
        )

        elapsed_ms: int = int((time.monotonic() - start) * 1000)
        logger.info(
            "retriever_search",
            question=question[:100],
            n_requested=n,
            result_count=len(chunks),
            elapsed_ms=elapsed_ms,
        )
        return chunks
