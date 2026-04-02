"""Unit tests for the ClinicalTrials.gov ingester — all HTTP calls mocked."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

import pytest

from backend.ingest.clinical_trials import ClinicalTrialsIngestor

_MOCK_CTGOV_RESPONSE: dict = {
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT01793935",
                    "briefTitle": "Withania Somnifera for Schizophrenia",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "completionDateStruct": {
                        "date": "2016-07-07",
                        "type": "ACTUAL",
                    },
                },
                "descriptionModule": {
                    "briefSummary": (
                        "This study examines whether ashwagandha extract "
                        "improves symptoms in patients with schizophrenia. "
                        "Eighty participants were randomized to receive "
                        "either standardized root extract or placebo for "
                        "twelve weeks in a double-blind trial design."
                    ),
                    "detailedDescription": (
                        "Eighty patients with schizophrenia were enrolled "
                        "in this randomized controlled trial. Primary "
                        "outcomes included PANSS total score reduction and "
                        "cognitive performance as measured by standardized "
                        "neuropsychological battery assessments."
                    ),
                },
            }
        },
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT02915315",
                    "briefTitle": "Ashwagandha for Bipolar Disorder",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "completionDateStruct": {
                        "date": "2019-03-15",
                        "type": "ACTUAL",
                    },
                },
                "descriptionModule": {
                    "briefSummary": (
                        "This pilot study evaluates ashwagandha root "
                        "extract as adjunctive treatment for cognitive "
                        "deficits in bipolar disorder patients during "
                        "euthymic periods with stable mood medication."
                    ),
                    "detailedDescription": (
                        "Sixty participants with bipolar I or II disorder "
                        "in euthymic phase received ashwagandha 300 mg "
                        "twice daily or matching placebo for eight weeks."
                    ),
                },
            }
        },
    ]
}

_MOCK_CTGOV_EMPTY: dict = {"studies": []}


def _mock_json_response(data: dict, status: int = 200) -> AsyncMock:
    """Create a mock httpx.Response with JSON data."""
    mock = AsyncMock()
    mock.text = json.dumps(data)
    mock.status_code = status
    mock.json = MagicMock(return_value=data)
    mock.raise_for_status = MagicMock()
    if status >= 400:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return mock


# ------------------------------------------------------------------
# Scenario 1 — happy path: studies returned, chunks produced
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ctgov_returns_chunks_from_mocked_json() -> None:
    """ClinicalTrials.gov ingester should return HerbChunks from mocked JSON."""
    with patch("backend.ingest.clinical_trials.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            return_value=_mock_json_response(_MOCK_CTGOV_RESPONSE)
        )

        ingester = ClinicalTrialsIngestor()
        chunks = await ingester.run(
            herb_list=["Ashwagandha"], max_per_herb=5
        )

        assert len(chunks) >= 1
        assert chunks[0].source_type == "ClinicalTrials.gov"
        assert chunks[0].id.startswith("ctgov-NCT")
        assert "clinicaltrials.gov/study/" in chunks[0].url
        assert chunks[0].herbs == ["Ashwagandha"]


@pytest.mark.asyncio
async def test_ctgov_chunk_ids_contain_nct_id() -> None:
    """Each chunk ID should embed the NCT identifier."""
    with patch("backend.ingest.clinical_trials.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            return_value=_mock_json_response(_MOCK_CTGOV_RESPONSE)
        )

        ingester = ClinicalTrialsIngestor()
        chunks = await ingester.run(
            herb_list=["Ashwagandha"], max_per_herb=5
        )

        nct_ids_found: set[str] = set()
        for c in chunks:
            # Extract NCT ID from chunk ID like "ctgov-NCT01793935-chunk-0"
            parts = c.id.split("-")
            nct_ids_found.add(parts[1])

        assert "NCT01793935" in nct_ids_found or "NCT02915315" in nct_ids_found


@pytest.mark.asyncio
async def test_ctgov_year_parsed_correctly() -> None:
    """Completion year should be extracted from the date struct."""
    with patch("backend.ingest.clinical_trials.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            return_value=_mock_json_response(_MOCK_CTGOV_RESPONSE)
        )

        ingester = ClinicalTrialsIngestor()
        chunks = await ingester.run(
            herb_list=["Ashwagandha"], max_per_herb=5
        )

        years: set[str] = {c.year for c in chunks}
        # Both studies have years 2016 and 2019
        assert years <= {"2016", "2019"}


# ------------------------------------------------------------------
# Scenario 2 — empty results: no completed trials
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ctgov_empty_results_returns_empty() -> None:
    """No completed trials should yield an empty chunk list."""
    with patch("backend.ingest.clinical_trials.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            return_value=_mock_json_response(_MOCK_CTGOV_EMPTY)
        )

        ingester = ClinicalTrialsIngestor()
        chunks = await ingester.run(
            herb_list=["ObscureHerb"], max_per_herb=5
        )

        assert chunks == []


# ------------------------------------------------------------------
# Scenario 3 — HTTP error: connection failure
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ctgov_http_error_returns_empty() -> None:
    """HTTP errors should be caught and logged, not crash."""
    with patch("backend.ingest.clinical_trials.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_client.get = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        ingester = ClinicalTrialsIngestor()
        chunks = await ingester.run(
            herb_list=["Ashwagandha"], max_per_herb=5
        )

        assert chunks == []
