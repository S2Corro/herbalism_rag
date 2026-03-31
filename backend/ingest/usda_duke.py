"""Herbalism RAG — USDA Duke Phytochemical Database Ingester.

Parses CSV files from the USDA Dr. Duke's Phytochemical and
Ethnobotanical Database, groups compounds by plant, and produces
``HerbChunk`` objects.

If CSV files don't exist in ``data/usda_duke/``, the ingester logs a
warning and returns an empty list — no crash.

**Expected CSV format**: columns for plant name, chemical compound,
and biological activity.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import structlog

from backend.ingest.chunker import chunk_text
from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_DUKE_URL: str = "https://phytochem.nal.usda.gov/"


class DukeIngestor:
    """Ingester for USDA Duke phytochemical CSV data.

    Reads CSV files from a directory, groups chemical compound and
    biological activity data by plant, and produces text chunks
    summarising each plant's phytochemistry.
    """

    def run(
        self,
        csv_path: str = "data/usda_duke/",
    ) -> list[HerbChunk]:
        """Parse Duke CSV files and return HerbChunks.

        Args:
            csv_path: Directory containing CSV files.

        Returns:
            List of ``HerbChunk`` objects with ``source_type="USDA Duke"``.
            Returns empty list if no CSVs found.
        """
        data_dir: Path = Path(csv_path)
        if not data_dir.is_dir():
            logger.warning("duke_dir_missing", path=str(data_dir))
            return []

        csv_files: list[Path] = list(data_dir.glob("*.csv"))
        if not csv_files:
            logger.warning("duke_no_csv_files", path=str(data_dir))
            return []

        logger.info("duke_ingest_start", csv_count=len(csv_files))

        plant_data: dict[str, list[str]] = defaultdict(list)

        for csv_file in csv_files:
            self._parse_csv(csv_file, plant_data)

        all_chunks: list[HerbChunk] = self._build_chunks(plant_data)

        logger.info(
            "duke_ingest_complete",
            plants=len(plant_data),
            chunks_produced=len(all_chunks),
        )
        return all_chunks

    def _parse_csv(
        self,
        csv_file: Path,
        plant_data: dict[str, list[str]],
    ) -> None:
        """Parse a single CSV file and accumulate plant data.

        Expects columns (case-insensitive): plant name, chemical
        compound, biological activity.  Rows missing key columns
        are skipped.

        Args:
            csv_file: Path to the CSV file.
            plant_data: Accumulator dict mapping plant names to
                text fragments.
        """
        try:
            with csv_file.open("r", encoding="utf-8", errors="replace") as f:
                reader: csv.DictReader[str] = csv.DictReader(f)
                headers: list[str] = [
                    h.lower().strip() for h in (reader.fieldnames or [])
                ]

                plant_col: str = self._find_column(
                    headers, ["plant", "plant name", "species"]
                )
                chem_col: str = self._find_column(
                    headers, ["chemical", "compound", "chemical compound"]
                )
                activity_col: str = self._find_column(
                    headers, ["activity", "biological activity", "bioactivity"]
                )

                if not plant_col:
                    logger.warning(
                        "duke_missing_plant_col", file=str(csv_file)
                    )
                    return

                for row in reader:
                    self._process_row(
                        row, plant_col, chem_col, activity_col, plant_data
                    )
        except (OSError, csv.Error) as exc:
            logger.error("duke_csv_error", file=str(csv_file), error=str(exc))

    def _process_row(
        self,
        row: dict[str, str],
        plant_col: str,
        chem_col: str,
        activity_col: str,
        plant_data: dict[str, list[str]],
    ) -> None:
        """Process a single CSV row into plant data.

        Args:
            row: CSV row dict.
            plant_col: Column name for plant.
            chem_col: Column name for chemical compound.
            activity_col: Column name for biological activity.
            plant_data: Accumulator dict.
        """
        plant: str = row.get(plant_col, "").strip()
        if not plant:
            return

        compound: str = row.get(chem_col, "").strip() if chem_col else ""
        activity: str = row.get(activity_col, "").strip() if activity_col else ""

        parts: list[str] = [f"{plant} contains {compound}"]
        if activity:
            parts.append(f"which has biological activities: {activity}")
        plant_data[plant].append(", ".join(parts) + ".")

    @staticmethod
    def _find_column(
        headers: list[str], candidates: list[str]
    ) -> str:
        """Find the first matching column name from candidates.

        Args:
            headers: Lowercased header names from the CSV.
            candidates: Possible column names to match.

        Returns:
            The original header string if found, empty string otherwise.
        """
        for candidate in candidates:
            for header in headers:
                if candidate in header:
                    return header
        return ""

    def _build_chunks(
        self,
        plant_data: dict[str, list[str]],
    ) -> list[HerbChunk]:
        """Build HerbChunks from grouped plant data.

        Joins all compound entries per plant into a single text block,
        then chunks for storage.

        Args:
            plant_data: Map of plant names to lists of compound text.

        Returns:
            List of HerbChunks.
        """
        chunks: list[HerbChunk] = []
        for plant, entries in sorted(plant_data.items()):
            full_text: str = " ".join(entries)
            text_chunks: list[str] = chunk_text(
                full_text, max_tokens=512, overlap_tokens=50, min_tokens=30
            )

            plant_slug: str = plant.lower().replace(" ", "_")[:50]
            for i, text in enumerate(text_chunks):
                chunks.append(HerbChunk(
                    id=f"duke-{plant_slug}-chunk-{i}",
                    text=text,
                    source_type="USDA Duke",
                    title=f"Phytochemical Profile: {plant}",
                    url=_DUKE_URL,
                    year="2023",
                    herbs=[plant],
                    chunk_index=i,
                ))
        return chunks
