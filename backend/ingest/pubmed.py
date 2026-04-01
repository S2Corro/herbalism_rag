"""Herbalism RAG — PubMed Abstract Ingester.

Fetches research abstracts from NCBI PubMed using the E-utilities API
(``esearch.fcgi`` → ``efetch.fcgi``), chunks them, and returns
``HerbChunk`` objects for ChromaDB storage.

**Rate limiting**: NCBI allows 3 requests/second without an API key.
This ingester adds a 0.35-second delay between requests.

**No API key required** for the low-volume queries used here.
"""

from __future__ import annotations

import asyncio
from typing import Any
from xml.etree import ElementTree

import httpx
import structlog

from backend.ingest.chunker import chunk_text
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_RATE_DELAY: float = 0.35  # seconds between requests (< 3 req/s limit)


class PubMedIngestor:
    """Ingester for PubMed research abstracts.

    Uses NCBI E-utilities to search for herb-related articles and
    fetch their abstracts.  Each abstract is chunked (most are short
    enough to produce a single chunk) and wrapped as a ``HerbChunk``.
    """

    async def run(
        self,
        herb_list: list[str],
        max_per_herb: int = 5,
    ) -> list[HerbChunk]:
        """Fetch PubMed abstracts for each herb and return HerbChunks.

        Args:
            herb_list: List of herb names to search for.
            max_per_herb: Maximum articles to fetch per herb.

        Returns:
            List of ``HerbChunk`` objects with ``source_type="PubMed"``.
        """
        all_chunks: list[HerbChunk] = []
        logger.info("pubmed_ingest_start", herbs=herb_list)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for herb in herb_list:
                try:
                    chunks = await self._fetch_herb(
                        client, herb, max_per_herb
                    )
                    all_chunks.extend(chunks)
                except Exception as exc:
                    logger.error(
                        "pubmed_herb_error", herb=herb, error=str(exc)
                    )

        logger.info(
            "pubmed_ingest_complete",
            chunks_produced=len(all_chunks),
        )
        return all_chunks

    async def _fetch_herb(
        self,
        client: httpx.AsyncClient,
        herb: str,
        max_results: int,
    ) -> list[HerbChunk]:
        """Search and fetch abstracts for a single herb.

        Args:
            client: Shared HTTP client.
            herb: Herb name to search for.
            max_results: Maximum number of articles.

        Returns:
            List of HerbChunks for this herb.
        """
        pmids: list[str] = await self._search(client, herb, max_results)
        if not pmids:
            logger.warning("pubmed_no_results", herb=herb)
            return []

        logger.info("pubmed_search_results", herb=herb, pmid_count=len(pmids))
        await asyncio.sleep(_RATE_DELAY)

        articles: list[dict[str, str]] = await self._fetch_abstracts(
            client, pmids
        )
        return self._articles_to_chunks(articles, herb)

    async def _search(
        self,
        client: httpx.AsyncClient,
        herb: str,
        max_results: int,
    ) -> list[str]:
        """Run an ESearch query and return PMIDs.

        Args:
            client: HTTP client.
            herb: Herb name for the search query.
            max_results: Maximum PMIDs to return.

        Returns:
            List of PMID strings.
        """
        query: str = f'"{herb}" AND (herbal OR medicinal OR phytotherapy)'
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "xml",
        }
        resp: httpx.Response = await client.get(
            f"{_BASE_URL}/esearch.fcgi", params=params
        )
        resp.raise_for_status()

        root: ElementTree.Element = ElementTree.fromstring(resp.text)
        return [id_el.text for id_el in root.findall(".//Id") if id_el.text]

    async def _fetch_abstracts(
        self,
        client: httpx.AsyncClient,
        pmids: list[str],
    ) -> list[dict[str, str]]:
        """Fetch article details for a list of PMIDs.

        Args:
            client: HTTP client.
            pmids: List of PubMed IDs.

        Returns:
            List of dicts with keys: pmid, title, abstract, year.
        """
        params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        resp: httpx.Response = await client.get(
            f"{_BASE_URL}/efetch.fcgi", params=params
        )
        resp.raise_for_status()
        return self._parse_articles_xml(resp.text)

    def _parse_articles_xml(self, xml_text: str) -> list[dict[str, str]]:
        """Parse EFetch XML into article dicts.

        Args:
            xml_text: Raw XML from efetch.

        Returns:
            List of article dicts with pmid, title, abstract, year.
        """
        articles: list[dict[str, str]] = []
        try:
            root: ElementTree.Element = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            logger.error("pubmed_xml_parse_error", error=str(exc))
            return []

        for article_el in root.findall(".//PubmedArticle"):
            pmid: str = self._get_text(article_el, ".//PMID")
            title: str = self._get_text(article_el, ".//ArticleTitle")
            abstract: str = self._get_text(article_el, ".//AbstractText")
            year: str = self._get_text(
                article_el, ".//PubDate/Year"
            ) or self._get_text(article_el, ".//PubDate/MedlineDate")

            if pmid and abstract:
                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "year": year or "Unknown",
                })
        return articles

    @staticmethod
    def _get_text(
        parent: ElementTree.Element, xpath: str
    ) -> str:
        """Safely extract text from an XML element.

        Args:
            parent: Parent XML element.
            xpath: XPath to the child element.

        Returns:
            Text content or empty string if not found.
        """
        el: ElementTree.Element | None = parent.find(xpath)
        return (el.text or "").strip() if el is not None else ""

    def _articles_to_chunks(
        self,
        articles: list[dict[str, str]],
        herb: str,
    ) -> list[HerbChunk]:
        """Convert parsed articles to HerbChunks.

        Args:
            articles: List of article dicts.
            herb: Herb name for metadata.

        Returns:
            List of HerbChunks.
        """
        chunks: list[HerbChunk] = []
        for article in articles:
            text_chunks: list[str] = chunk_text(
                article["abstract"],
                max_tokens=512,
                overlap_tokens=50,
                min_tokens=30,
            )
            for i, text in enumerate(text_chunks):
                chunks.append(HerbChunk(
                    id=f"pubmed-{article['pmid']}-chunk-{i}",
                    text=text,
                    source_type="PubMed",
                    title=article["title"],
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/",
                    year=article["year"],
                    herbs=[herb],
                    chunk_index=i,
                ))
        return chunks
