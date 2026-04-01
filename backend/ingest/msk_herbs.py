"""Herbalism RAG — MSK About Herbs Ingester.

Scrapes clinical monograph pages from Memorial Sloan Kettering's
"About Herbs" database using ``httpx`` + ``beautifulsoup4``, chunks the
extracted text, and returns ``HerbChunk`` objects.

MSK pages are structured HTML with clinical summaries — if the page
structure changes, the parser logs a warning and skips that herb rather
than crashing.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from backend.ingest.chunker import chunk_text
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_BASE_URL: str = (
    "https://www.mskcc.org/cancer-care/diagnosis-treatment/"
    "symptom-management/integrative-medicine/herbs/"
)
_RATE_DELAY: float = 1.0  # Be respectful to MSK servers

_DEFAULT_HERBS: list[str] = [
    "ashwagandha", "turmeric", "ginger", "echinacea", "ginkgo-biloba",
    "garlic", "valerian", "st-johns-wort", "chamomile", "ginseng",
    "green-tea", "milk-thistle", "saw-palmetto", "black-cohosh",
    "evening-primrose", "feverfew", "kava", "licorice-root",
    "flaxseed", "aloe-vera",
]


class MSKIngestor:
    """Ingester for MSK About Herbs clinical monographs.

    Scrapes herb pages from the MSK website, extracts the clinical
    summary text, and produces ``HerbChunk`` objects for storage.
    """

    async def run(
        self,
        herb_list: list[str] | None = None,
    ) -> list[HerbChunk]:
        """Scrape MSK herb pages and return HerbChunks.

        Args:
            herb_list: URL slugs for herbs (e.g. ``["ashwagandha"]``).
                If None, uses the default list of 20 common herbs.

        Returns:
            List of ``HerbChunk`` objects with ``source_type="MSK"``.
        """
        herbs: list[str] = herb_list or _DEFAULT_HERBS
        all_chunks: list[HerbChunk] = []
        logger.info("msk_ingest_start", herb_count=len(herbs))

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "HerbalismRAG/0.1 (research)"},
        ) as client:
            for herb_slug in herbs:
                try:
                    chunks = await self._scrape_herb(client, herb_slug)
                    all_chunks.extend(chunks)
                except Exception as exc:
                    logger.error(
                        "msk_herb_error", herb=herb_slug, error=str(exc)
                    )
                await asyncio.sleep(_RATE_DELAY)

        logger.info(
            "msk_ingest_complete",
            chunks_produced=len(all_chunks),
        )
        return all_chunks

    async def _scrape_herb(
        self,
        client: httpx.AsyncClient,
        herb_slug: str,
    ) -> list[HerbChunk]:
        """Fetch and parse a single MSK herb page.

        Args:
            client: Shared HTTP client.
            herb_slug: URL-friendly herb name (e.g. ``"ashwagandha"``).

        Returns:
            List of HerbChunks for this herb.
        """
        url: str = f"{_BASE_URL}{herb_slug}"
        resp: httpx.Response = await client.get(url)
        resp.raise_for_status()

        return self._parse_page(resp.text, herb_slug, url)

    def _parse_page(
        self,
        html: str,
        herb_slug: str,
        url: str,
    ) -> list[HerbChunk]:
        """Extract text from MSK herb page HTML and produce chunks.

        Falls back gracefully if the expected page structure is missing.

        Args:
            html: Raw HTML content.
            herb_slug: Herb slug for ID generation.
            url: Full URL for citation.

        Returns:
            List of HerbChunks, or empty list if parsing fails.
        """
        soup: BeautifulSoup = BeautifulSoup(html, "html.parser")

        # Try to extract the herb name from the page title
        title_el: Any = soup.find("h1") or soup.find("title")
        title: str = title_el.get_text(strip=True) if title_el else herb_slug

        # Extract content from article body or main content area
        content_el: Any = (
            soup.find("article")
            or soup.find("div", class_="field-item")
            or soup.find("main")
        )

        if not content_el:
            logger.warning("msk_no_content", herb=herb_slug, url=url)
            return []

        # Extract paragraph text
        paragraphs: list[str] = [
            p.get_text(strip=True)
            for p in content_el.find_all("p")
            if p.get_text(strip=True)
        ]
        full_text: str = " ".join(paragraphs)

        if not full_text.strip():
            logger.warning("msk_empty_text", herb=herb_slug)
            return []

        text_chunks: list[str] = chunk_text(
            full_text, max_tokens=512, overlap_tokens=50, min_tokens=30
        )

        herb_name: str = herb_slug.replace("-", " ").title()
        return [
            HerbChunk(
                id=f"msk-{herb_slug}-chunk-{i}",
                text=chunk,
                source_type="MSK",
                title=title,
                url=url,
                year="2024",
                herbs=[herb_name],
                chunk_index=i,
            )
            for i, chunk in enumerate(text_chunks)
        ]
