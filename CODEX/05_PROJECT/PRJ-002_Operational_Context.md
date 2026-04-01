---
id: PRJ-002
title: "Herbalism RAG — Operational Context & Institutional Knowledge"
type: explanation
status: APPROVED
owner: architect
agents: [all]
tags: [project-management, context, operations, institutional-knowledge]
related: [PRJ-001, BLU-001, BLU-002, RUN-002]
created: 2026-04-01
updated: 2026-04-01
version: 1.0.0
---

> **BLUF:** This is the "state of the world" document. If you are a new Architect Agent starting a fresh conversation, read this first. It captures every operational decision, gotcha, and institutional fact that isn't in the blueprints or governance docs.

# Operational Context & Institutional Knowledge

## 1. Project Status (as of 2026-04-01)

| Phase | Sprint | Status | Tests | Merged To |
|:------|:-------|:-------|:------|:----------|
| 1. Scaffold | SPR-001 | ✅ COMPLETE | 6 | master |
| 2. Domain + Repository | SPR-002 | ✅ COMPLETE | 23 (29 total) | master |
| 3. Ingestion Services | SPR-003 | ✅ COMPLETE | 14 (43 total) | master |
| 4. RAG Services | SPR-004 | ✅ COMPLETE | 22 (65 total) | master |
| 5. API Controllers | SPR-005 | 🟡 ACTIVE | — | pending |
| 6. Frontend | SPR-006 | 🟡 ACTIVE | — | pending |
| 7. Integration | SPR-007 | ⬜ NOT STARTED | — | — |

**Total tests on master:** 65 (all passing)
**Total application code files:** 15 Python modules + 1 JSON seed file + 1 script
**Total test files:** 11

---

## 2. Architecture Decisions Made During Development

### 2.1 ChromaDB `embedding_function=None`
**Decision:** HerbRepository creates its ChromaDB collection with `embedding_function=None`.
**Rationale:** We provide raw embedding vectors via RetrieverService (sentence-transformers). We never want ChromaDB to auto-download ONNX models or compute its own embeddings.
**Consequence:** The `add()` method must include embeddings, OR the ingest script must pre-compute them. The current `add()` stores documents without embeddings (ChromaDB 1.5.5 handles this), and embeddings are provided at query time via `search(query_embedding=vector)`.
**Reference:** DEF-002 documents the version sensitivity of this decision.

### 2.2 Sentence-Transformers Model: `all-MiniLM-L6-v2`
**Decision:** Local CPU-based embedding model, 384 dimensions.
**Rationale:** Free, fast, no API key needed, good enough for semantic search.
**Note:** The model is ~80MB. First run downloads it to `~/.cache/huggingface/`. Subsequent runs use cache. CI/CD would need to pre-cache this.

### 2.3 Claude Model: `claude-haiku-20240307`
**Decision:** Use Claude Haiku (cheapest, fastest) for answer synthesis.
**Rationale:** This is a RAG app — the LLM just synthesizes from retrieved context, it doesn't need to be the smartest model. Haiku keeps costs low.
**API key:** Required in `.env` as `ANTHROPIC_API_KEY`. Tests use a fake key.

### 2.4 WHO Seed Data Instead of Live Scraping
**Decision:** Ship static `data/seeds/who_monographs.json` (10 herbs, ~25KB) as seed data.
**Rationale:** WHO doesn't have a public API. The seed data guarantees the app always has some content, even without network access. The 10 herbs (Ashwagandha, Turmeric, Ginger, Echinacea, Ginkgo, Garlic, Valerian, St. John's Wort, Chamomile, Peppermint) produce 30+ chunks.

### 2.5 USDA Duke Data Gap
**Decision:** The DukeIngestor gracefully returns empty when CSVs don't exist.
**Status:** No USDA Duke CSV data has been sourced yet. The ingestor code is ready but waiting for data from the Ag Data Commons bulk download.
**Action needed:** Source CSV files into `data/usda_duke/` to activate this ingester.

### 2.6 Modular Monolith — Not Microservices
**Decision:** Single FastAPI process serves backend + static frontend.
**Rationale:** This is a personal/educational tool, not a high-scale production service. A monolith keeps deployment simple (single `uvicorn` process).

---

## 3. Workspace Topology

```
/home/ubuntu/projects/
├── herbalism_rag/               ← ARCHITECT (docs, CODEX)
├── herbalism_rag_dev/           ← DEVELOPER A (code)
└── herbalism_rag_dev_secondary/ ← DEVELOPER B (code)
```

**Remote:** `https://github.com/S2Corro/herbalism_rag.git`
**Branch model:** `master` is the integration branch. Developers create `feature/SPR-NNN-TNNN-*` branches.
**Merge strategy:** `--no-ff` merge commits so sprint boundaries are visible in git log.

See **RUN-002** for the full multi-workspace operations runbook.

---

## 4. Known Gotchas

### 4.1 ChromaDB Version Sensitivity
- `requirements.txt` pins `chromadb==1.5.5` (upgraded from 0.5.23 via DEF-002)
- ChromaDB 0.5.x breaks `upsert()` when `embedding_function=None`
- If a dev workspace has a stale venv with 0.5.x, 5 tests will fail
- Fix: `pip install chromadb==1.5.5 --force-reinstall`

### 4.2 Venv Staleness
- Each workspace has its own `.venv/`
- When `requirements.txt` changes, venvs must be manually updated
- Symptom: tests pass in one workspace but fail in another
- Fix: `pip install -r requirements.txt --upgrade`

### 4.3 beautifulsoup4 Install Gap
- Listed in `requirements.txt` but in SPR-001's original venv setup, transitive deps sometimes didn't resolve it
- Dev Agent A had to install it manually during SPR-003
- Fix: always run full `pip install -r requirements.txt` after pull

### 4.4 ANTHROPIC_API_KEY in Tests
- All test files set `os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"` BEFORE importing backend modules
- This prevents `config.py` from raising a `ValueError` on missing env var
- The import order matters: set env var → import backend modules

### 4.5 sentence-transformers Model Download
- First run downloads `all-MiniLM-L6-v2` (~80MB) from HuggingFace
- Tests that use the real model (test_retriever.py) will be slow on first run
- Subsequent runs use the cached model in `~/.cache/huggingface/`

### 4.6 Frontend Static Files
- FastAPI mounts `frontend/` as static files at `/`
- This mount is set up in `backend/main.py`
- The frontend directory currently contains placeholder files from SPR-001

---

## 5. Dependency State (as of 2026-04-01)

| Package | Pinned Version | Purpose |
|:--------|:---------------|:--------|
| fastapi | 0.115.6 | Web framework |
| uvicorn[standard] | 0.32.1 | ASGI server |
| pydantic-settings | 2.7.0 | Config from .env |
| chromadb | 1.5.5 | Vector store (upgraded from 0.5.23) |
| sentence-transformers | 3.3.1 | Local embeddings |
| anthropic | 0.42.0 | Claude API client |
| httpx | 0.28.1 | HTTP client + test client |
| beautifulsoup4 | 4.12.3 | HTML parsing (MSK scraper) |
| structlog | 24.4.0 | Structured logging |
| pytest | 8.3.4 | Test framework |
| pytest-asyncio | 0.24.0 | Async test support |

---

## 6. Codebase Map (master branch)

```
backend/
├── __init__.py
├── config.py                    ← Settings from .env (ANTHROPIC_API_KEY, paths)
├── main.py                      ← FastAPI app, GET /api/status, static mount
├── api/
│   ├── routes/                  ← Empty — SPR-005 will add query.py, herbs.py
│   └── schemas/
│       ├── requests.py          ← QueryRequest (Pydantic, validated)
│       └── responses.py         ← Source, QueryResponse, StatusResponse
├── db/
│   └── herb_repository.py       ← HerbRepository wrapping ChromaDB
├── ingest/
│   ├── chunker.py               ← Sentence-aware text splitter
│   ├── who_seeds.py             ← WHO monograph seed data loader
│   ├── pubmed.py                ← PubMed E-utilities async ingester
│   ├── msk_herbs.py             ← MSK About Herbs scraper
│   └── usda_duke.py             ← USDA Duke CSV parser (no data yet)
├── models/
│   └── herb_chunk.py            ← HerbChunk dataclass (domain model)
└── rag/
    ├── retriever.py             ← RetrieverService (embed + search)
    ├── generator.py             ← GeneratorService (Claude synthesis)
    └── pipeline.py              ← RAGPipeline orchestrator

data/
└── seeds/
    └── who_monographs.json      ← 10 herb monographs (committed to git)

scripts/
└── ingest.py                    ← Runs all ingesters, stores in ChromaDB

tests/                           ← 11 test files, 65 tests
frontend/                        ← Placeholder — SPR-006 builds this
```

---

## 7. Git History Summary

| Commit | Description |
|:-------|:------------|
| `1f7a5d4` | SPR-005/006 sprint docs added |
| `e2bbaeb` | MANIFEST update: SPR-003/004 COMPLETE |
| `b03f4a7` | merge(SPR-004): RAG services |
| `a80a277` | merge(SPR-003): Ingestion services |
| `2b40cc8` | fix(DEF-002): chromadb pin upgrade |
| `8007f2a` | merge(SPR-002): Domain + Repository |
| `3dcfc71` | merge(SPR-001): Project scaffold |

---

## 8. What Comes After SPR-005 + SPR-006

### SPR-007: Integration & Verification (Final Sprint)
1. Run `scripts/ingest.py` to populate ChromaDB with real data
2. Start the app (`uvicorn backend.main:app`)
3. Test 10 end-to-end queries through the frontend
4. Verify all source URLs resolve
5. Final code cleanup and push to GitHub
6. Record a demo video or screenshot walkthrough

### Post-Project Considerations
- **USDA Duke data:** Need to source CSV from Ag Data Commons
- **Model caching:** For deployment, pre-download the sentence-transformers model
- **Rate limiting:** PubMed E-utilities allows 3 req/sec without API key
- **Security:** ANTHROPIC_API_KEY must remain server-side only — never exposed to frontend

---

## 9. Change Log

| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| 2026-04-01 | 1.0.0 | Initial operational context document | Architect Agent |
