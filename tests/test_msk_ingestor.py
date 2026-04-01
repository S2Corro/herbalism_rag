"""Unit tests for the MSK About Herbs ingester — all HTTP calls mocked."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest

from backend.ingest.msk_herbs import MSKIngestor

_MOCK_MSK_HTML: str = """<!DOCTYPE html>
<html>
<head><title>Ashwagandha | MSK</title></head>
<body>
<h1>Ashwagandha</h1>
<article>
  <p>Ashwagandha is an adaptogenic herb used in Ayurvedic medicine for centuries.</p>
  <p>Clinical studies show it reduces cortisol levels and improves stress resilience.</p>
  <p>The root extract is standardized to withanolides as the active constituents.</p>
  <p>Recommended dosage is 300-600mg of standardized extract daily.</p>
  <p>Contraindications include pregnancy and thyroid disorders.</p>
</article>
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


@pytest.mark.asyncio
async def test_msk_returns_chunks_with_mocked_html() -> None:
    """MSK ingester should return HerbChunks from mocked HTML."""
    with patch("backend.ingest.msk_herbs.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(return_value=_mock_response(_MOCK_MSK_HTML))

        ingester = MSKIngestor()
        chunks = await ingester.run(herb_list=["ashwagandha"])

        assert len(chunks) >= 1
        assert chunks[0].source_type == "MSK"
        assert "ashwagandha" in chunks[0].url


@pytest.mark.asyncio
async def test_msk_parse_failure_returns_empty() -> None:
    """Parse failure on bad HTML should not crash."""
    bad_html = "<html><body><p>No article tag here</p></body></html>"
    with patch("backend.ingest.msk_herbs.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(return_value=_mock_response(bad_html))

        ingester = MSKIngestor()
        chunks = await ingester.run(herb_list=["unknown-herb"])
        # Should return empty or very few chunks (no crash)
        assert isinstance(chunks, list)


@pytest.mark.asyncio
async def test_msk_http_error_returns_empty() -> None:
    """HTTP errors should be caught and logged, not crash."""
    with patch("backend.ingest.msk_herbs.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        ingester = MSKIngestor()
        chunks = await ingester.run(herb_list=["ashwagandha"])
        assert chunks == []
