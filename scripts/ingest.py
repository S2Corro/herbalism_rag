#!/usr/bin/env python3
"""Herbalism RAG — Ingestion Orchestration Script.

Runs all ingesters in sequence, stores results in ChromaDB via
HerbRepository, and reports summary statistics.

Usage::

    python scripts/ingest.py
    python -m scripts.ingest

Execution order:
    1. WHO seed data (always — no network needed)
    2. PubMed abstracts (requires network)
    3. MSK About Herbs (requires network)
    4. USDA Duke CSVs (if files exist)

Each ingester failure is caught and logged — a single failing source
does not kill the entire pipeline.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import structlog

# Ensure the project root is on sys.path so imports work when run as a script
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.config import settings  # noqa: E402
from backend.db.herb_repository import HerbRepository  # noqa: E402
from backend.ingest.msk_herbs import MSKIngestor  # noqa: E402
from backend.ingest.pubmed import PubMedIngestor  # noqa: E402
from backend.ingest.usda_duke import DukeIngestor  # noqa: E402
from backend.ingest.who_seeds import WHOSeedIngestor  # noqa: E402
from backend.models.herb_chunk import HerbChunk  # noqa: E402

# Configure structlog for script output
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

_DEFAULT_HERBS: list[str] = [
    "Ashwagandha", "Turmeric", "Ginger", "Echinacea", "Ginkgo",
    "Garlic", "Valerian", "St. John's Wort", "Chamomile", "Ginseng",
]


async def _run_async_ingesters(
    all_chunks: list[HerbChunk],
) -> None:
    """Run the async ingesters (PubMed, MSK).

    Args:
        all_chunks: Accumulator list — chunks are appended in place.
    """
    # PubMed
    try:
        pubmed: PubMedIngestor = PubMedIngestor()
        pubmed_chunks: list[HerbChunk] = await pubmed.run(
            herb_list=_DEFAULT_HERBS, max_per_herb=3
        )
        all_chunks.extend(pubmed_chunks)
        logger.info("ingest_pubmed_done", chunks=len(pubmed_chunks))
    except Exception as exc:
        logger.error("ingest_pubmed_failed", error=str(exc))

    # MSK
    try:
        msk: MSKIngestor = MSKIngestor()
        msk_chunks: list[HerbChunk] = await msk.run()
        all_chunks.extend(msk_chunks)
        logger.info("ingest_msk_done", chunks=len(msk_chunks))
    except Exception as exc:
        logger.error("ingest_msk_failed", error=str(exc))


def main() -> None:
    """Run the full ingestion pipeline."""
    start: float = time.monotonic()
    logger.info("ingest_pipeline_start")

    all_chunks: list[HerbChunk] = []

    # 1. WHO seeds (always works — no network)
    try:
        who: WHOSeedIngestor = WHOSeedIngestor()
        who_chunks: list[HerbChunk] = who.run()
        all_chunks.extend(who_chunks)
        logger.info("ingest_who_done", chunks=len(who_chunks))
    except Exception as exc:
        logger.error("ingest_who_failed", error=str(exc))

    # 2 & 3. PubMed + MSK (async)
    asyncio.run(_run_async_ingesters(all_chunks))

    # 4. USDA Duke (sync, if CSVs exist)
    try:
        duke: DukeIngestor = DukeIngestor()
        duke_chunks: list[HerbChunk] = duke.run()
        all_chunks.extend(duke_chunks)
        logger.info("ingest_duke_done", chunks=len(duke_chunks))
    except Exception as exc:
        logger.error("ingest_duke_failed", error=str(exc))

    # Store in ChromaDB
    if all_chunks:
        repo: HerbRepository = HerbRepository(
            chroma_db_path=str(settings.chroma_db_path),
            collection_name=settings.collection_name,
        )
        repo.add(all_chunks)
        stats: dict[str, object] = repo.stats()
        logger.info("ingest_stored", stats=stats)
    else:
        logger.warning("ingest_no_chunks")

    elapsed: float = time.monotonic() - start
    logger.info(
        "ingest_pipeline_complete",
        total_chunks=len(all_chunks),
        elapsed_seconds=round(elapsed, 1),
    )


if __name__ == "__main__":
    main()
