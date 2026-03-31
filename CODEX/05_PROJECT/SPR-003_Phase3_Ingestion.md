---
id: SPR-003
title: "Phase 3 — Ingestion Services"
type: how-to
status: ACTIVE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, ingestion, pubmed, msk, usda, who]
related: [SPR-002, PRJ-001, BLU-001, BLU-002, RES-001]
created: 2026-03-31
updated: 2026-03-31
version: 1.0.0
---

> **BLUF:** Sprint 003 builds the data ingestion pipeline — four ingesters (PubMed, MSK, USDA Duke, WHO) plus a runner script. Exit criterion: `scripts/ingest.py` populates ChromaDB with 500+ chunks carrying full citation metadata. **This sprint runs in parallel with SPR-004. Do NOT modify files outside the `backend/ingest/` and `scripts/` directories.**

# Sprint 003: Phase 3 — Ingestion Services

**Phase:** 3 — Ingestion Services
**Target:** Scope-bounded (AI-agent pace)
**Agent(s):** Developer Agent A (Ingestion)
**Dependencies:** SPR-002 (HerbChunk + HerbRepository must be on `master`)
**Blueprints:** BLU-001 §4 (directory), BLU-002 §2 (embedding), BLU-002 §7 (chunking), RES-001 (data sources)

---

## ⚠️ Parallel Execution Warning

> [!CAUTION]
> **This sprint runs in parallel with SPR-004 (RAG Services), executed by a different Developer Agent.**
> - You MUST NOT modify any files outside `backend/ingest/`, `scripts/`, `data/seeds/`, and `tests/test_ingest*.py`.
> - You MUST NOT modify `backend/main.py`, `backend/db/herb_repository.py`, `backend/models/herb_chunk.py`, or any file in `backend/rag/`.
> - If you need changes to shared files, file an `EVO-` doc and stop.
> - Branch from `master` at sprint start. Do NOT rebase against SPR-004 branches.

---

## ⚠️ Mandatory Compliance — Every Task

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | Referential integrity (§12.1): every doc ID referenced must exist. |
| **GOV-002** | Unit tests for each ingester. Mock all HTTP calls — no real network requests in tests. |
| **GOV-003** | Type annotations, docstrings, max 60 LOC per function. |
| **GOV-004** | Ingesters must handle HTTP errors, parse failures, and empty responses gracefully. No silent failures. |
| **GOV-005** | Branch per task: `feature/SPR-003-TNNN-description`. Commits: `feat(SPR-003): T-NNN description`. |
| **GOV-006** | Each ingester must log: start, source URL/count, chunks produced, errors encountered. Use `structlog`. |
| **GOV-007** | Update task status as you work. Blockers → `DEF-` doc. |
| **GOV-008** | No new pip dependencies — `httpx`, `beautifulsoup4`, `sentence-transformers` are already in `requirements.txt`. |

---

## Developer Agent Tasks

### T-001: Create text chunking utility
- **Branch:** `feature/SPR-003-T001-chunker`
- **Dependencies:** None
- **Blueprints:** BLU-002 §7 (chunking strategy)
- **Deliverable:**
  - `backend/ingest/chunker.py` — a reusable text chunking function
  - Function signature:
    ```python
    def chunk_text(
        text: str,
        max_tokens: int = 512,
        overlap_tokens: int = 50,
        min_tokens: int = 100,
    ) -> list[str]:
    ```
  - Sentence-aware splitting: split on sentence boundaries (`. `, `? `, `! `), never mid-sentence
  - Overlap: last `overlap_tokens` worth of text from previous chunk prepended to next chunk
  - Discard fragments shorter than `min_tokens`
  - Use simple whitespace tokenization (`len(text.split())`) for token counting — no external tokenizer needed
- **Acceptance criteria:**
  - A 1000-word text produces 2-3 chunks of ~512 tokens each
  - No chunk ends mid-sentence
  - Chunks shorter than 100 tokens are discarded
  - Overlap is present between consecutive chunks
- **Status:** [ ] Not Started

---

### T-002: Create WHO seed data ingester
- **Branch:** `feature/SPR-003-T002-who-ingester`
- **Dependencies:** T-001
- **Blueprints:** RES-001 §WHO
- **Deliverable:**
  - `data/seeds/who_monographs.json` — curated seed data (committed to git)
    - At least 10 herb entries, each with: `name`, `title`, `text` (monograph content), `url`, `year`
    - Cover common herbs: Ashwagandha, Turmeric, Ginger, Echinacea, Ginkgo, Garlic, Valerian, St. John's Wort, Chamomile, Peppermint
    - Text should be realistic monograph-style content (therapeutic uses, dosage, safety, contraindications)
    - Each entry should produce 2-5 chunks when processed
  - `backend/ingest/who_seeds.py` — ingester class
    ```python
    class WHOSeedIngestor:
        def run(self, json_path: str = "data/seeds/who_monographs.json") -> list[HerbChunk]:
            """Load WHO seed data, chunk, and return HerbChunks."""
    ```
  - Uses `chunker.py` for text splitting
  - Sets `source_type="WHO"` on all chunks
  - ID format: `who-{herb_name_lower}-chunk-{index}`
- **Acceptance criteria:**
  - `WHOSeedIngestor().run()` returns 30+ HerbChunks
  - All chunks have complete metadata (source_type, title, url, year, herbs)
  - JSON file is valid and parseable
- **Status:** [ ] Not Started

---

### T-003: Create PubMed ingester
- **Branch:** `feature/SPR-003-T003-pubmed-ingester`
- **Dependencies:** T-001
- **Blueprints:** RES-001 §PubMed
- **Deliverable:**
  - `backend/ingest/pubmed.py` — ingester class
    ```python
    class PubMedIngestor:
        async def run(self, herb_list: list[str], max_per_herb: int = 5) -> list[HerbChunk]:
            """Fetch PubMed abstracts for each herb and return HerbChunks."""
    ```
  - Uses NCBI E-utilities: `esearch.fcgi` → get PMIDs, then `efetch.fcgi` → get abstracts
  - Base URL: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
  - Rate limit: max 3 requests per second (no API key needed for low volume)
  - Search query format: `"{herb}" AND (herbal OR medicinal OR phytotherapy)`
  - Uses `httpx.AsyncClient` for HTTP calls
  - Uses `chunker.py` for text splitting (most abstracts are short enough to be 1 chunk)
  - ID format: `pubmed-{pmid}-chunk-{index}`
  - Sets `source_type="PubMed"`, `url="https://pubmed.ncbi.nlm.nih.gov/{pmid}/"`
  - Handles: HTTP errors, empty results, XML parse failures
  - Logs: herb being searched, articles found, chunks produced, errors
- **Acceptance criteria:**
  - `PubMedIngestor().run(["Ashwagandha"], max_per_herb=2)` returns HerbChunks (when network is available)
  - All chunks have PMID-based URLs
  - HTTP errors don't crash the ingester (logged and skipped)
- **Status:** [ ] Not Started

---

### T-004: Create MSK About Herbs ingester
- **Branch:** `feature/SPR-003-T004-msk-ingester`
- **Dependencies:** T-001
- **Blueprints:** RES-001 §MSK
- **Deliverable:**
  - `backend/ingest/msk_herbs.py` — ingester class
    ```python
    class MSKIngestor:
        async def run(self, herb_list: list[str] | None = None) -> list[HerbChunk]:
            """Scrape MSK About Herbs pages and return HerbChunks."""
    ```
  - Scrapes `https://www.mskcc.org/cancer-care/diagnosis-treatment/symptom-management/integrative-medicine/herbs/`
  - Uses `httpx.AsyncClient` for HTTP, `beautifulsoup4` for parsing
  - Extracts: herb name, clinical summary text, URL
  - Falls back gracefully if page structure changes (log warning, skip herb)
  - Uses `chunker.py` for text splitting
  - ID format: `msk-{herb_name_lower}-chunk-{index}`
  - Sets `source_type="MSK"`
  - If `herb_list` is None, uses a default list of 20 common herbs
- **Acceptance criteria:**
  - Ingester produces HerbChunks with MSK URLs
  - Parse failures are logged, not crashed
  - Works with the default herb list
- **Status:** [ ] Not Started

---

### T-005: Create USDA Duke ingester
- **Branch:** `feature/SPR-003-T005-duke-ingester`
- **Dependencies:** T-001
- **Blueprints:** RES-001 §USDA Duke
- **Deliverable:**
  - `backend/ingest/usda_duke.py` — ingester class
    ```python
    class DukeIngestor:
        def run(self, csv_path: str = "data/usda_duke/") -> list[HerbChunk]:
            """Parse Duke CSV files and return HerbChunks."""
    ```
  - Reads CSV files from `data/usda_duke/` directory
  - Expected CSV columns: plant name, chemical compound, biological activity
  - Constructs text chunks by grouping compounds per plant: "Plant X contains compound Y, which has biological activities: Z"
  - If CSV files don't exist, log a warning and return empty list (graceful degradation)
  - ID format: `duke-{plant_name_lower}-chunk-{index}`
  - Sets `source_type="USDA Duke"`, `url="https://phytochem.nal.usda.gov/"`
- **Acceptance criteria:**
  - Returns empty list with warning log when CSV files absent (no crash)
  - When CSVs exist, produces HerbChunks with plant-based grouping
- **Status:** [ ] Not Started

---

### T-006: Create `scripts/ingest.py` — orchestration script
- **Branch:** `feature/SPR-003-T006-ingest-script`
- **Dependencies:** T-002, T-003, T-004, T-005
- **Deliverable:**
  - `scripts/ingest.py` — runs all ingesters in sequence, stores results in ChromaDB
  - Flow:
    1. Import all ingesters + HerbRepository
    2. Initialize HerbRepository (uses settings from config.py)
    3. Run WHO seed ingester (always — no network needed)
    4. Run PubMed ingester (with default herb list)
    5. Run MSK ingester (with default herb list)
    6. Run Duke ingester (if CSVs exist)
    7. Log total: chunks per source, total chunks, elapsed time
  - Default herb list for PubMed/MSK: `["Ashwagandha", "Turmeric", "Ginger", "Echinacea", "Ginkgo", "Garlic", "Valerian", "St. John's Wort", "Chamomile", "Ginseng"]`
  - Runnable via: `python -m scripts.ingest` or `python scripts/ingest.py`
  - Each ingester failure must not kill the entire script (catch, log, continue)
- **Acceptance criteria:**
  - `python scripts/ingest.py` runs without crashing
  - WHO seed data always produces chunks (no network needed)
  - After running, `HerbRepository.stats()` shows chunk counts per source
  - Total chunks ≥ 30 (at minimum from WHO seeds alone)
- **Status:** [ ] Not Started

---

### T-007: Write unit tests for ingesters
- **Branch:** `feature/SPR-003-T007-tests`
- **Dependencies:** T-001 through T-006
- **Deliverable:**
  - `tests/test_chunker.py`:
    - Test sentence-aware splitting
    - Test overlap between chunks
    - Test min_tokens discard
    - Test single-sentence text (no split)
  - `tests/test_who_ingestor.py`:
    - Test with the real `who_monographs.json` seed file
    - Verify chunk count, metadata completeness
  - `tests/test_pubmed_ingestor.py`:
    - **Mock all HTTP calls** using `pytest-httpx` or `unittest.mock.patch`
    - Test with mocked XML response
    - Test HTTP error handling (return empty, don't crash)
  - `tests/test_msk_ingestor.py`:
    - **Mock all HTTP calls**
    - Test with mocked HTML response
    - Test parse failure handling
  - All tests use fake API key
  - No real network calls in tests
- **Acceptance criteria:**
  - `pytest tests/ -v` passes ALL tests (including SPR-001 and SPR-002 tests)
  - Minimum 12 new test functions
  - No test makes a real HTTP call
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 Chunker | Developer A | [ ] | `feature/SPR-003-T001-chunker` | [ ] |
| T-002 WHO ingester | Developer A | [ ] | `feature/SPR-003-T002-who-ingester` | [ ] |
| T-003 PubMed ingester | Developer A | [ ] | `feature/SPR-003-T003-pubmed-ingester` | [ ] |
| T-004 MSK ingester | Developer A | [ ] | `feature/SPR-003-T004-msk-ingester` | [ ] |
| T-005 Duke ingester | Developer A | [ ] | `feature/SPR-003-T005-duke-ingester` | [ ] |
| T-006 Ingest script | Developer A | [ ] | `feature/SPR-003-T006-ingest-script` | [ ] |
| T-007 Tests | Developer A | [ ] | `feature/SPR-003-T007-tests` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

- [ ] All 7 tasks pass their acceptance criteria
- [ ] `scripts/ingest.py` runs without crashing
- [ ] WHO seeds produce ≥ 30 chunks
- [ ] `pytest tests/ -v` passes ALL tests (SPR-001 + SPR-002 + SPR-003)
- [ ] No real HTTP calls in tests
- [ ] No files modified outside `backend/ingest/`, `scripts/`, `data/seeds/`, `tests/test_ingest*.py`, `tests/test_chunker.py`, `tests/test_who*.py`, `tests/test_pubmed*.py`, `tests/test_msk*.py`
- [ ] No hardcoded secrets
- [ ] All GOV compliance requirements met
- [ ] No open `DEF-` reports against this sprint

---

## Audit Notes (Architect)

[Architect fills this in after Developer submits for review.]

**Verdict:** PENDING
**Deploy approved:** NO — pending audit
