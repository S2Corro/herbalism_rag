"""Herbalism RAG — NCCIH (NIH) Herbs at a Glance Ingester.

Scrapes NIH National Center for Complementary and Integrative Health
"Herbs at a Glance" fact sheets using ``httpx`` + ``beautifulsoup4``,
chunks the extracted text, and returns ``HerbChunk`` objects.

NCCIH pages are well-structured HTML with clinical summaries.  If the
page structure changes or a herb page doesn't exist, the ingester logs
a warning and skips that herb rather than crashing the pipeline.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from backend.ingest.chunker import chunk_text
from backend.ingest.herb_list import HERB_NAMES
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_BASE_URL: str = "https://www.nccih.nih.gov/health/"
_RATE_DELAY: float = 0.5  # seconds between requests
_USER_AGENT: str = "HerbalismRAG/0.1 (research)"


def _name_to_slug(name: str) -> str:
    """Convert a display name to a URL-safe slug.

    Examples::

        >>> _name_to_slug("St. John's Wort")
        'st-johns-wort'
        >>> _name_to_slug("Aloe Vera")
        'aloe-vera'

    Args:
        name: Human-readable herb name.

    Returns:
        Lowercased, hyphenated slug with punctuation removed.
    """
    slug: str = name.lower()
    slug = slug.replace("'", "").replace(".", "")
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


class NCCIHIngestor:
    """Ingester for NCCIH Herbs at a Glance fact sheets.

    Scrapes herb pages from the NIH NCCIH website, extracts the main
    content text, chunks it, and produces ``HerbChunk`` objects for
    storage in ChromaDB.
    """

    async def run(
        self,
        herb_list: list[str] | None = None,
    ) -> list[HerbChunk]:
        """Scrape NCCIH herb pages and return HerbChunks.

        Args:
            herb_list: Display names for herbs (e.g. ``["Ashwagandha"]``).
                If None, uses the canonical herb list.

        Returns:
            List of ``HerbChunk`` objects with ``source_type="NCCIH"``.
        """
        herbs: list[str] = herb_list or HERB_NAMES
        all_chunks: list[HerbChunk] = []
        logger.info("nccih_ingest_start", herb_count=len(herbs))

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            for herb_name in herbs:
                try:
                    chunks = await self._scrape_herb(client, herb_name)
                    all_chunks.extend(chunks)
                except Exception as exc:
                    logger.error(
                        "nccih_herb_error",
                        herb=herb_name,
                        error=str(exc),
                    )
                await asyncio.sleep(_RATE_DELAY)

        logger.info(
            "nccih_ingest_complete",
            chunks_produced=len(all_chunks),
        )
        return all_chunks

    async def _scrape_herb(
        self,
        client: httpx.AsyncClient,
        herb_name: str,
    ) -> list[HerbChunk]:
        """Fetch and parse a single NCCIH herb page.

        Args:
            client: Shared HTTP client.
            herb_name: Display name of the herb.

        Returns:
            List of HerbChunks for this herb.  Empty if the page
            doesn't exist (404) or has no extractable content.
        """
        slug: str = _name_to_slug(herb_name)
        url: str = f"{_BASE_URL}{slug}"

        resp: httpx.Response = await client.get(url)
        if resp.status_code == 404:
            logger.warning("nccih_page_not_found", herb=herb_name, url=url)
            return []
        resp.raise_for_status()

        return self._parse_page(resp.text, herb_name, slug, url)

    def _parse_page(
        self,
        html: str,
        herb_name: str,
        herb_slug: str,
        url: str,
    ) -> list[HerbChunk]:
        """Extract text from NCCIH herb page HTML and produce chunks.

        Falls back gracefully if the expected page structure is missing.

        Args:
            html: Raw HTML content.
            herb_name: Display name for metadata.
            herb_slug: Slug for chunk ID generation.
            url: Full URL for citation.

        Returns:
            List of HerbChunks, or empty list if parsing fails.
        """
        soup: BeautifulSoup = BeautifulSoup(html, "html.parser")

        # Extract page title
        title_el: Any = soup.find("h1") or soup.find("title")
        title: str = title_el.get_text(strip=True) if title_el else herb_name

        # Extract content from the main content area
        content_el: Any = (
            soup.find("article")
            or soup.find("div", class_="field-item")
            or soup.find("main")
        )

        if not content_el:
            logger.warning("nccih_no_content", herb=herb_name, url=url)
            return []

        # Extract paragraph text
        paragraphs: list[str] = [
            p.get_text(strip=True)
            for p in content_el.find_all("p")
            if p.get_text(strip=True)
        ]
        full_text: str = " ".join(paragraphs)

        if not full_text.strip():
            logger.warning("nccih_empty_text", herb=herb_name)
            return []

        text_chunks: list[str] = chunk_text(
            full_text, max_tokens=512, overlap_tokens=50, min_tokens=30
        )

        return [
            HerbChunk(
                id=f"nccih-{herb_slug}-chunk-{i}",
                text=chunk,
                source_type="NCCIH",
                title=title,
                url=url,
                year="2024",
                herbs=[herb_name],
                chunk_index=i,
            )
            for i, chunk in enumerate(text_chunks)
        ]
