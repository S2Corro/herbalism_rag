"""Unit tests for the PubMed ingester — all HTTP calls mocked."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest

from backend.ingest.pubmed import PubMedIngestor

_MOCK_ESEARCH_XML: str = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult>
  <IdList>
    <Id>12345678</Id>
    <Id>87654321</Id>
  </IdList>
</eSearchResult>"""

_MOCK_EFETCH_XML: str = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Effects of Ashwagandha on Cortisol</ArticleTitle>
        <Abstract>
          <AbstractText>Ashwagandha root extract significantly reduced serum cortisol levels in stressed adults in this randomized double-blind placebo-controlled trial conducted over sixty days.  Participants receiving 300 mg twice daily showed a 30 percent reduction in cortisol compared to placebo group. The herb also demonstrated anxiolytic effects comparable to standard therapies.</AbstractText>
        </Abstract>
        <Journal><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


def _mock_response(text: str, status: int = 200) -> AsyncMock:
    """Create a mock httpx.Response."""
    mock = AsyncMock()
    mock.text = text
    mock.status_code = status
    mock.raise_for_status = MagicMock()  # sync call in source code
    if status >= 400:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return mock


@pytest.mark.asyncio
async def test_pubmed_returns_chunks_with_mocked_http() -> None:
    """PubMed ingester should return HerbChunks from mocked XML."""
    with patch("backend.ingest.pubmed.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            side_effect=[
                _mock_response(_MOCK_ESEARCH_XML),
                _mock_response(_MOCK_EFETCH_XML),
            ]
        )

        ingester = PubMedIngestor()
        chunks = await ingester.run(["Ashwagandha"], max_per_herb=2)

        assert len(chunks) >= 1
        assert chunks[0].source_type == "PubMed"
        assert "12345678" in chunks[0].url


@pytest.mark.asyncio
async def test_pubmed_http_error_returns_empty() -> None:
    """HTTP errors should not crash — return empty list."""
    with patch("backend.ingest.pubmed.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        ingester = PubMedIngestor()
        chunks = await ingester.run(["Ashwagandha"], max_per_herb=2)
        assert chunks == []

