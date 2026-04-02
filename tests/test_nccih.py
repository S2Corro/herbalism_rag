"""Unit tests for the NCCIH Herbs at a Glance ingester — all HTTP calls mocked."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest

from backend.ingest.nccih import NCCIHIngestor, _name_to_slug

_MOCK_NCCIH_HTML: str = """<!DOCTYPE html>
<html>
<head><title>Ashwagandha | NCCIH</title></head>
<body>
<h1>Ashwagandha</h1>
<article>
  <p>Ashwagandha is an adaptogenic herb used in Ayurvedic medicine for centuries.
  It has been studied for stress reduction, anxiety, and cognitive function.
  Clinical trials show ashwagandha root extract significantly reduces serum
  cortisol levels and improves overall well-being in chronically stressed adults.</p>
  <p>The root is standardized to withanolides as the primary bioactive constituents.
  Multiple randomized controlled trials demonstrate a 30 percent reduction in
  cortisol after 60 days of supplementation at 300 mg twice daily.  The herb
  also exhibits immunomodulatory and neuroprotective properties.</p>
  <p>Recommended dosage is 300-600mg of standardized extract daily.
  Contraindications include pregnancy, thyroid disorders, and autoimmune conditions.
  Side effects are generally mild and may include gastrointestinal discomfort.
  Long-term safety data beyond 3 months is limited.</p>
</article>
</body>
</html>"""

_MOCK_EMPTY_HTML: str = """<!DOCTYPE html>
<html>
<head><title>Empty Page</title></head>
<body>
<h1>No Content Here</h1>
<article></article>
</body>
</html>"""


def _mock_response(text: str, status: int = 200) -> AsyncMock:
    """Create a mock httpx.Response."""
    mock = AsyncMock()
    mock.text = text
    mock.status_code = status
    mock.raise_for_status = MagicMock()
    if status >= 400:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return mock


# ------------------------------------------------------------------
# Slug conversion
# ------------------------------------------------------------------


class TestNameToSlug:
    """Verify the display-name → URL-slug conversion."""

    def test_simple_name(self) -> None:
        assert _name_to_slug("Ashwagandha") == "ashwagandha"

    def test_multi_word(self) -> None:
        assert _name_to_slug("Aloe Vera") == "aloe-vera"

    def test_apostrophe_and_period(self) -> None:
        assert _name_to_slug("St. John's Wort") == "st-johns-wort"

    def test_cats_claw(self) -> None:
        assert _name_to_slug("Cat's Claw") == "cats-claw"


# ------------------------------------------------------------------
# Scenario 1 — happy path: page exists, chunks produced
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nccih_returns_chunks_with_mocked_html() -> None:
    """NCCIH ingester should return HerbChunks from mocked HTML."""
    with patch("backend.ingest.nccih.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(return_value=_mock_response(_MOCK_NCCIH_HTML))

        ingester = NCCIHIngestor()
        chunks = await ingester.run(herb_list=["Ashwagandha"])

        assert len(chunks) >= 1
        assert chunks[0].source_type == "NCCIH"
        assert chunks[0].id.startswith("nccih-ashwagandha-chunk-")
        assert "ashwagandha" in chunks[0].url
        assert chunks[0].herbs == ["Ashwagandha"]
        assert chunks[0].year == "2024"


# ------------------------------------------------------------------
# Scenario 2 — 404: page doesn't exist for this herb
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nccih_404_returns_empty() -> None:
    """A 404 response should return empty list, not raise."""
    with patch("backend.ingest.nccih.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(return_value=_mock_response("", status=404))

        ingester = NCCIHIngestor()
        chunks = await ingester.run(herb_list=["UnknownHerb"])

        assert chunks == []


# ------------------------------------------------------------------
# Scenario 3 — empty content: page exists but has no text
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nccih_empty_content_returns_empty() -> None:
    """Page with no paragraph content should return empty list."""
    with patch("backend.ingest.nccih.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(return_value=_mock_response(_MOCK_EMPTY_HTML))

        ingester = NCCIHIngestor()
        chunks = await ingester.run(herb_list=["EmptyHerb"])

        assert chunks == []


# ------------------------------------------------------------------
# Scenario 4 — HTTP error: connection failure
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nccih_http_error_returns_empty() -> None:
    """HTTP errors should be caught and logged, not crash."""
    with patch("backend.ingest.nccih.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        ingester = NCCIHIngestor()
        chunks = await ingester.run(herb_list=["Ashwagandha"])

        assert chunks == []
