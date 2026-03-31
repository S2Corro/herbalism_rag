"""Herbalism RAG — Herb Repository (ChromaDB).

The single contact point between the application and ChromaDB.  No other
module should import or call the ChromaDB SDK directly — all vector-store
operations go through this repository.

Follows the Repository pattern from BLU-001 §5: the repository speaks
the domain language (``HerbChunk``) and hides all storage implementation
details from the service layer above.
"""

from __future__ import annotations

import time
from typing import Any

import chromadb
import structlog

from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class HerbRepository:
    """Repository wrapping a ChromaDB persistent collection.

    Provides typed CRUD-style methods that accept and return
    ``HerbChunk`` domain objects.  All ChromaDB SDK calls are
    encapsulated here.

    Args:
        chroma_db_path: Filesystem path for persistent storage.
        collection_name: Name of the ChromaDB collection.

    Attributes:
        client: The ChromaDB ``PersistentClient`` instance.
        collection: The active ChromaDB ``Collection``.
    """

    def __init__(
        self,
        chroma_db_path: str = "data/chroma_db",
        collection_name: str = "herbalism",
    ) -> None:
        """Initialize the repository and ChromaDB collection.

        Creates or opens a persistent ChromaDB client at the specified
        path and gets-or-creates the named collection.

        Args:
            chroma_db_path: Filesystem path for the persistent store.
            collection_name: Name of the collection to use.

        Raises:
            RuntimeError: If ChromaDB client or collection init fails.
        """
        try:
            self.client: chromadb.ClientAPI = chromadb.PersistentClient(
                path=chroma_db_path,
            )
            self.collection: chromadb.Collection = (
                self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=None,  # We provide raw vectors; skip ONNX model
                )
            )
            logger.info(
                "repository_initialized",
                chroma_db_path=chroma_db_path,
                collection=collection_name,
                doc_count=self.collection.count(),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize ChromaDB at '{chroma_db_path}': {exc}"
            ) from exc

    def add(self, chunks: list[HerbChunk]) -> int:
        """Add herb chunks to the ChromaDB collection (upsert).

        Duplicate IDs are overwritten (upsert behavior), so calling
        ``add()`` with the same chunks twice does not create duplicates.

        Args:
            chunks: List of ``HerbChunk`` objects to store.

        Returns:
            The number of chunks added.

        Raises:
            RuntimeError: If the ChromaDB upsert operation fails.
        """
        if not chunks:
            return 0

        start: float = time.monotonic()
        try:
            self.collection.upsert(
                ids=[c.id for c in chunks],
                documents=[c.text for c in chunks],
                metadatas=[c.to_chroma_metadata() for c in chunks],
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to add {len(chunks)} chunks to ChromaDB: {exc}"
            ) from exc

        elapsed_ms: int = int((time.monotonic() - start) * 1000)
        logger.info(
            "repository_add",
            count=len(chunks),
            elapsed_ms=elapsed_ms,
        )
        return len(chunks)

    def search(
        self,
        query_embedding: list[float],
        n: int = 8,
    ) -> list[HerbChunk]:
        """Search the collection by embedding vector.

        Returns the top-*n* most similar ``HerbChunk`` objects using
        ChromaDB's built-in cosine similarity.

        Args:
            query_embedding: The query vector (384-d for MiniLM).
            n: Maximum number of results to return.

        Returns:
            List of ``HerbChunk`` objects, ordered by similarity
            (most similar first).  Empty list if no results.

        Raises:
            RuntimeError: If the ChromaDB query fails.
        """
        if n <= 0:
            return []

        start: float = time.monotonic()
        try:
            results: dict[str, Any] = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n,
            )
        except Exception as exc:
            raise RuntimeError(
                f"ChromaDB search failed: {exc}"
            ) from exc

        elapsed_ms: int = int((time.monotonic() - start) * 1000)

        ids: list[str] = results.get("ids", [[]])[0]
        documents: list[str] = results.get("documents", [[]])[0]
        metadatas: list[dict[str, Any]] = results.get("metadatas", [[]])[0]

        chunks: list[HerbChunk] = [
            HerbChunk.from_chroma(id=id_, document=doc, metadata=meta)
            for id_, doc, meta in zip(ids, documents, metadatas)
        ]

        logger.info(
            "repository_search",
            result_count=len(chunks),
            elapsed_ms=elapsed_ms,
        )
        return chunks

    def list_herbs(self) -> list[str]:
        """Return a sorted, deduplicated list of all herb names.

        Queries all metadata in the collection, extracts the ``herbs``
        field (comma-separated string), splits and deduplicates, and
        returns a sorted list.

        Returns:
            Sorted list of unique herb names across all chunks.

        Raises:
            RuntimeError: If the ChromaDB metadata query fails.
        """
        try:
            all_data: dict[str, Any] = self.collection.get(
                include=["metadatas"],
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to list herbs from ChromaDB: {exc}"
            ) from exc

        herbs_set: set[str] = set()
        for meta in all_data.get("metadatas", []):
            herbs_raw: str = str(meta.get("herbs", ""))
            if herbs_raw:
                for herb in herbs_raw.split(","):
                    stripped: str = herb.strip()
                    if stripped:
                        herbs_set.add(stripped)

        return sorted(herbs_set)

    def stats(self) -> dict[str, object]:
        """Return collection statistics.

        Returns:
            Dict with ``doc_count`` (total chunks) and ``sources``
            (count per ``source_type``).

        Raises:
            RuntimeError: If the ChromaDB metadata query fails.
        """
        try:
            all_data: dict[str, Any] = self.collection.get(
                include=["metadatas"],
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to get stats from ChromaDB: {exc}"
            ) from exc

        source_counts: dict[str, int] = {}
        for meta in all_data.get("metadatas", []):
            src: str = str(meta.get("source_type", "unknown"))
            source_counts[src] = source_counts.get(src, 0) + 1

        return {
            "doc_count": self.collection.count(),
            "sources": source_counts,
        }
