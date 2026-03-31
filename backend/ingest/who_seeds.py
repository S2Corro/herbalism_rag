"""Herbalism RAG — WHO Seed Data Ingester.

Loads curated WHO monograph data from ``data/seeds/who_monographs.json``,
chunks the text using the sentence-aware chunker, and returns a list of
``HerbChunk`` objects ready for ChromaDB storage.

This ingester requires **no network access** — the seed data is committed
to the repository.  It should always be run first in the ingestion pipeline
to guarantee a baseline of curated, high-quality chunks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from backend.ingest.chunker import chunk_text
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class WHOSeedIngestor:
    """Ingester for curated WHO monograph seed data.

    Reads a JSON file containing herb monograph entries, chunks each
    entry's text, and produces ``HerbChunk`` objects with full citation
    metadata.

    The JSON format is a list of objects, each with:
    ``name``, ``title``, ``text``, ``url``, ``year``.
    """

    def run(
        self,
        json_path: str = "data/seeds/who_monographs.json",
    ) -> list[HerbChunk]:
        """Load WHO seed data, chunk text, and return HerbChunks.

        Args:
            json_path: Path to the WHO monographs JSON file.

        Returns:
            List of ``HerbChunk`` objects with ``source_type="WHO"``.
            Returns empty list if the file is missing or invalid.
        """
        path: Path = Path(json_path)
        if not path.is_file():
            logger.warning("who_seed_file_missing", path=str(path))
            return []

        logger.info("who_ingest_start", path=str(path))

        try:
            raw: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("who_seed_parse_error", error=str(exc))
            return []

        all_chunks: list[HerbChunk] = []

        for entry in raw:
            entry_chunks: list[HerbChunk] = self._process_entry(entry)
            all_chunks.extend(entry_chunks)

        logger.info(
            "who_ingest_complete",
            entries=len(raw),
            chunks_produced=len(all_chunks),
        )
        return all_chunks

    def _process_entry(
        self, entry: dict[str, Any]
    ) -> list[HerbChunk]:
        """Chunk a single monograph entry into HerbChunks.

        Args:
            entry: A dict with keys: name, title, text, url, year.

        Returns:
            List of HerbChunks for this entry.
        """
        name: str = entry.get("name", "Unknown")
        title: str = entry.get("title", "WHO Monograph")
        text: str = entry.get("text", "")
        url: str = entry.get("url", "")
        year: str = entry.get("year", "")

        if not text.strip():
            logger.warning("who_entry_empty_text", herb=name)
            return []

        text_chunks: list[str] = chunk_text(
            text, max_tokens=120, overlap_tokens=20, min_tokens=30
        )

        herb_name_lower: str = name.lower().replace(" ", "_").replace("'", "")
        return [
            HerbChunk(
                id=f"who-{herb_name_lower}-chunk-{i}",
                text=chunk,
                source_type="WHO",
                title=title,
                url=url,
                year=year,
                herbs=[name],
                chunk_index=i,
            )
            for i, chunk in enumerate(text_chunks)
        ]
