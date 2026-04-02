"""Herbalism RAG — ClinicalTrials.gov Ingester.

Pulls completed herbal supplement trials from the ClinicalTrials.gov
REST API v2, chunks the study summaries, and returns ``HerbChunk``
objects.  Unlike the HTML scrapers (MSK, NCCIH), this ingester works
with structured JSON responses — no BeautifulSoup required.

**Rate limiting**: 0.5-second delay between requests.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from backend.ingest.chunker import chunk_text
from backend.ingest.herb_list import HERB_NAMES
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_API_URL: str = "https://clinicaltrials.gov/api/v2/studies"
_RATE_DELAY: float = 0.5  # seconds between requests
_USER_AGENT: str = "HerbalismRAG/0.1 (research)"


class ClinicalTrialsIngestor:
    """Ingester for ClinicalTrials.gov completed herbal trials.

    Queries the ClinicalTrials.gov v2 REST API for completed studies
    matching each herb, extracts the brief and detailed descriptions,
    chunks the combined text, and produces ``HerbChunk`` objects.
    """

    async def run(
        self,
        herb_list: list[str] | None = None,
        max_per_herb: int = 5,
    ) -> list[HerbChunk]:
        """Fetch completed trials for each herb and return HerbChunks.

        Args:
            herb_list: Display names for herbs.  If None, uses the
                canonical herb list.
            max_per_herb: Maximum studies to fetch per herb.

        Returns:
            List of ``HerbChunk`` objects with
            ``source_type="ClinicalTrials.gov"``.
        """
        herbs: list[str] = herb_list or HERB_NAMES
        all_chunks: list[HerbChunk] = []
        logger.info("ctgov_ingest_start", herb_count=len(herbs))

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            for herb_name in herbs:
                try:
                    chunks = await self._fetch_herb(
                        client, herb_name, max_per_herb
                    )
                    all_chunks.extend(chunks)
                except Exception as exc:
                    logger.error(
                        "ctgov_herb_error",
                        herb=herb_name,
                        error=str(exc),
                    )
                await asyncio.sleep(_RATE_DELAY)

        logger.info(
            "ctgov_ingest_complete",
            chunks_produced=len(all_chunks),
        )
        return all_chunks

    async def _fetch_herb(
        self,
        client: httpx.AsyncClient,
        herb_name: str,
        max_results: int,
    ) -> list[HerbChunk]:
        """Query ClinicalTrials.gov for a single herb.

        Args:
            client: Shared HTTP client.
            herb_name: Display name of the herb.
            max_results: Maximum number of studies to retrieve.

        Returns:
            List of HerbChunks for this herb.  Empty if no completed
            trials exist.
        """
        params: dict[str, Any] = {
            "query.intr": herb_name,
            "filter.overallStatus": "COMPLETED",
            "pageSize": max_results,
            "format": "json",
        }

        resp: httpx.Response = await client.get(_API_URL, params=params)
        resp.raise_for_status()

        data: dict[str, Any] = resp.json()
        studies: list[dict[str, Any]] = data.get("studies", [])

        if not studies:
            logger.info("ctgov_no_studies", herb=herb_name)
            return []

        return self._studies_to_chunks(studies, herb_name)

    def _studies_to_chunks(
        self,
        studies: list[dict[str, Any]],
        herb_name: str,
    ) -> list[HerbChunk]:
        """Convert ClinicalTrials.gov study JSON to HerbChunks.

        Args:
            studies: List of study dicts from the API response.
            herb_name: Display name for metadata.

        Returns:
            List of HerbChunks.
        """
        chunks: list[HerbChunk] = []

        for study in studies:
            protocol: dict[str, Any] = study.get("protocolSection", {})

            id_module: dict[str, Any] = protocol.get(
                "identificationModule", {}
            )
            nct_id: str = id_module.get("nctId", "")
            title: str = id_module.get("briefTitle", "")

            if not nct_id:
                continue

            desc_module: dict[str, Any] = protocol.get(
                "descriptionModule", {}
            )
            summary: str = desc_module.get("briefSummary", "")
            detailed: str = desc_module.get("detailedDescription", "")

            status_module: dict[str, Any] = protocol.get(
                "statusModule", {}
            )
            completion_date: dict[str, str] = status_module.get(
                "completionDateStruct", {}
            )
            year: str = completion_date.get("date", "")[:4] or "Unknown"

            full_text: str = f"{title}. {summary} {detailed}".strip()
            if not full_text or full_text == ".":
                continue

            text_chunks: list[str] = chunk_text(
                full_text,
                max_tokens=512,
                overlap_tokens=50,
                min_tokens=30,
            )

            url: str = f"https://clinicaltrials.gov/study/{nct_id}"

            for i, text in enumerate(text_chunks):
                chunks.append(
                    HerbChunk(
                        id=f"ctgov-{nct_id}-chunk-{i}",
                        text=text,
                        source_type="ClinicalTrials.gov",
                        title=title,
                        url=url,
                        year=year,
                        herbs=[herb_name],
                        chunk_index=i,
                    )
                )

        return chunks
