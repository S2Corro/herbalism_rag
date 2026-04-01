"""Unit tests for the WHO seed data ingester."""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from backend.ingest.who_seeds import WHOSeedIngestor


def test_who_ingester_produces_chunks() -> None:
    """WHO ingester should produce 30+ chunks from the seed file."""
    chunks = WHOSeedIngestor().run()
    assert len(chunks) >= 30, f"Expected >=30 chunks, got {len(chunks)}"


def test_who_ingester_metadata_complete() -> None:
    """Every WHO chunk must have complete citation metadata."""
    chunks = WHOSeedIngestor().run()
    for c in chunks:
        assert c.source_type == "WHO"
        assert c.url, f"Empty url for chunk {c.id}"
        assert c.year, f"Empty year for chunk {c.id}"
        assert c.herbs, f"Empty herbs for chunk {c.id}"
        assert c.title, f"Empty title for chunk {c.id}"
        assert c.text, f"Empty text for chunk {c.id}"


def test_who_ingester_missing_file() -> None:
    """Missing JSON file should return empty list, not crash."""
    chunks = WHOSeedIngestor().run("/nonexistent/path.json")
    assert chunks == []
