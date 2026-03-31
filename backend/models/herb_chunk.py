"""Herbalism RAG — HerbChunk Domain Model.

The core data structure representing a single chunk of herb-related text
from any ingested source (PubMed, MSK, USDA Duke, WHO). HerbChunks flow
through every layer of the system:

- **Ingest layer** creates them from raw source data.
- **Repository layer** stores/retrieves them via ChromaDB.
- **Service layer** passes them to the LLM for synthesis.
- **Controller layer** serializes them as ``Source`` objects in API responses.

ChromaDB metadata values must be str, int, or float — so ``herbs`` (a list)
is stored as a comma-separated string and reconstructed on retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HerbChunk:
    """A single chunk of herb-related text from an ingested source.

    Each chunk represents a passage of up to ~512 tokens extracted from a
    larger document.  The ``id`` field encodes provenance:
    ``{source_type}-{identifier}-chunk-{index}``.

    Attributes:
        id: Unique identifier encoding source and position.
            Format: ``{source_type}-{identifier}-chunk-{index}``.
        text: The actual text excerpt (up to ~512 tokens).
        source_type: Origin database — one of
            ``"PubMed"``, ``"MSK"``, ``"USDA Duke"``, ``"WHO"``.
        title: Document or article title.
        url: Direct link to the source document.
        year: Publication year as a string (some sources lack year data).
        herbs: List of herb names mentioned in this chunk.
        chunk_index: Zero-based position within the original document.
    """

    id: str
    text: str
    source_type: str
    title: str
    url: str
    year: str
    herbs: list[str] = field(default_factory=list)
    chunk_index: int = 0

    def to_source(self) -> dict[str, str]:
        """Convert to a source-citation dict for API responses.

        Returns a dictionary with the fields needed to render a source
        card in the frontend.  The ``excerpt`` is truncated to the first
        300 characters of ``text``.

        Returns:
            Dict with keys: ``source_type``, ``title``, ``url``,
            ``year``, ``excerpt``.
        """
        return {
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "year": self.year,
            "excerpt": self.text[:300],
        }

    def to_chroma_metadata(self) -> dict[str, str | int]:
        """Serialize fields to a ChromaDB-compatible metadata dict.

        ChromaDB metadata values must be ``str``, ``int``, or ``float``.
        The ``herbs`` list is joined into a comma-separated string.
        The ``text`` field is excluded — it is stored as the ChromaDB
        ``document``, not as metadata.

        Returns:
            Dict with keys: ``source_type``, ``title``, ``url``,
            ``year``, ``herbs``, ``chunk_index``.
        """
        return {
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "year": self.year,
            "herbs": ",".join(self.herbs),
            "chunk_index": self.chunk_index,
        }

    @classmethod
    def from_chroma(
        cls,
        id: str,
        document: str,
        metadata: dict[str, str | int],
    ) -> HerbChunk:
        """Reconstruct a HerbChunk from ChromaDB query results.

        This is the inverse of ``to_chroma_metadata()``.  The ``herbs``
        field is split from a comma-separated string back into a list.
        Empty herb strings produce an empty list (not ``[""]``).

        Args:
            id: The chunk ID stored in ChromaDB.
            document: The stored document text.
            metadata: The metadata dict returned by ChromaDB.

        Returns:
            A fully reconstructed ``HerbChunk`` instance.
        """
        herbs_raw: str = str(metadata.get("herbs", ""))
        herbs: list[str] = (
            [h.strip() for h in herbs_raw.split(",") if h.strip()]
            if herbs_raw
            else []
        )

        return cls(
            id=id,
            text=document,
            source_type=str(metadata.get("source_type", "")),
            title=str(metadata.get("title", "")),
            url=str(metadata.get("url", "")),
            year=str(metadata.get("year", "")),
            herbs=herbs,
            chunk_index=int(metadata.get("chunk_index", 0)),
        )
