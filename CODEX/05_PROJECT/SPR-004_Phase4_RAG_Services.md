---
id: SPR-004
title: "Phase 4 — RAG Services"
type: how-to
status: ACTIVE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, rag, retriever, generator, embeddings, claude]
related: [SPR-002, PRJ-001, BLU-001, BLU-002]
created: 2026-03-31
updated: 2026-03-31
version: 1.0.0
---

> **BLUF:** Sprint 004 builds the RAG query pipeline — RetrieverService (local embeddings + ChromaDB search), GeneratorService (Claude Haiku synthesis with citations), and RAGPipeline orchestrator. Exit criterion: `RAGPipeline.run("What herb helps with cortisol?")` returns a cited answer with source metadata, verified by unit tests. **This sprint runs in parallel with SPR-003. Do NOT modify files outside `backend/rag/` and tests.**

# Sprint 004: Phase 4 — RAG Services

**Phase:** 4 — RAG Services
**Target:** Scope-bounded (AI-agent pace)
**Agent(s):** Developer Agent B (RAG)
**Dependencies:** SPR-002 (HerbChunk + HerbRepository must be on `master`)
**Blueprints:** BLU-001 §5 (layer contracts), BLU-002 §1-§5 (full RAG pipeline)

---

## ⚠️ Parallel Execution Warning

> [!CAUTION]
> **This sprint runs in parallel with SPR-003 (Ingestion Services), executed by a different Developer Agent.**
> - You MUST NOT modify any files outside `backend/rag/` and `tests/test_retriever.py`, `tests/test_generator.py`, `tests/test_pipeline.py`.
> - You MUST NOT modify `backend/main.py`, `backend/db/herb_repository.py`, `backend/models/herb_chunk.py`, or any file in `backend/ingest/`.
> - If you need changes to shared files, file an `EVO-` doc and stop.
> - Branch from `master` at sprint start. Do NOT rebase against SPR-003 branches.

---

## ⚠️ Mandatory Compliance — Every Task

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | Referential integrity (§12.1): every doc ID referenced must exist. |
| **GOV-002** | Unit tests for each service. Mock the Anthropic API — no real LLM calls in tests. |
| **GOV-003** | Type annotations, docstrings, max 60 LOC per function. |
| **GOV-004** | Services must handle embedding failures, API errors, and empty results gracefully. Typed exceptions. |
| **GOV-005** | Branch per task: `feature/SPR-004-TNNN-description`. Commits: `feat(SPR-004): T-NNN description`. |
| **GOV-006** | Each service must log operations via `structlog`: queries processed, timing, errors. |
| **GOV-007** | Update task status as you work. Blockers → `DEF-` doc. |
| **GOV-008** | No new pip dependencies — `sentence-transformers`, `anthropic`, and `chromadb` are already in `requirements.txt`. |

---

## Developer Agent Tasks

### T-001: Create `backend/rag/retriever.py` — RetrieverService
- **Branch:** `feature/SPR-004-T001-retriever`
- **Dependencies:** None (uses HerbRepository from SPR-002)
- **Blueprints:** BLU-002 §2 (embedding), BLU-002 §3 (retrieval)
- **Deliverable:**
  - `backend/rag/retriever.py` — service class
  - Class:
    ```python
    class RetrieverService:
        def __init__(self, repository: HerbRepository, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
            """Initialize with a HerbRepository and load the embedding model."""
            # Load sentence-transformers model (lazy or eager — your call)
            # Store repository reference

        def embed(self, text: str) -> list[float]:
            """Embed a text string into a 384-dimensional vector."""

        def search(self, question: str, n: int = 8) -> list[HerbChunk]:
            """Embed the question, search ChromaDB, return top-n HerbChunks."""
    ```
  - `embed()` uses `sentence-transformers` `SentenceTransformer` to encode text
  - `search()` calls `self.embed(question)` then `self.repository.search(embedding, n)`
  - Logs: model loaded, search query, result count, embedding time, search time
  - Handles: model load failure (typed exception), empty results
- **Acceptance criteria:**
  - `RetrieverService.embed("test")` returns a list of 384 floats
  - `RetrieverService.search("cortisol")` returns `list[HerbChunk]` (may be empty if no data)
  - Model loads without downloading (uses cached model if available)
- **Status:** [ ] Not Started

---

### T-002: Create `backend/rag/generator.py` — GeneratorService
- **Branch:** `feature/SPR-004-T002-generator`
- **Dependencies:** None
- **Blueprints:** BLU-002 §4 (Claude prompt), BLU-002 §5 (response schema)
- **Deliverable:**
  - `backend/rag/generator.py` — service class
  - Class:
    ```python
    class GeneratorService:
        def __init__(self, api_key: str, model: str = "claude-haiku-20240307"):
            """Initialize the Anthropic client."""

        async def synthesize(self, question: str, chunks: list[HerbChunk]) -> str:
            """Send question + chunks to Claude, return cited answer text."""
    ```
  - Builds the prompt exactly as specified in BLU-002 §4:
    - System prompt: "You are a herbalism research assistant. Answer using ONLY the provided sources..."
    - User prompt: Question + numbered source excerpts
  - Uses `anthropic.AsyncAnthropic` client
  - Extracts the text content from Claude's response
  - If chunks list is empty, returns a message saying "No relevant sources found"
  - Logs: question length, chunk count, Claude response time, token usage
  - Handles: API errors (rate limit, auth), empty responses
  - Max tokens for response: 1024
- **Acceptance criteria:**
  - `GeneratorService.synthesize(question, chunks)` returns a string answer
  - Prompt includes numbered sources matching BLU-002 §4 format
  - Empty chunks list returns "No relevant sources found" without API call
  - API errors raise typed exceptions with clear messages
- **Status:** [ ] Not Started

---

### T-003: Create `backend/rag/pipeline.py` — RAGPipeline
- **Branch:** `feature/SPR-004-T003-pipeline`
- **Dependencies:** T-001, T-002
- **Blueprints:** BLU-001 §5 (service layer contract), BLU-002 §1 (end-to-end flow)
- **Deliverable:**
  - `backend/rag/pipeline.py` — orchestrator class
  - Class:
    ```python
    class RAGPipeline:
        def __init__(self, retriever: RetrieverService, generator: GeneratorService):
            """Initialize with retriever and generator services."""

        async def run(self, question: str) -> QueryResponse:
            """Execute the full RAG pipeline: embed → search → synthesize → respond.

            Returns a QueryResponse with answer, sources, and timing.
            """
    ```
  - Flow:
    1. Start timer
    2. Call `self.retriever.search(question)` → chunks
    3. Call `self.generator.synthesize(question, chunks)` → answer
    4. Build `QueryResponse(answer=answer, sources=[c.to_source() for c in chunks], query_time_ms=elapsed)`
    5. Return response
  - Uses `QueryResponse` from `backend.api.schemas.responses`
  - Logs: question (truncated to 100 chars), chunk count, total pipeline time
  - Handles: retriever errors, generator errors — wraps and re-raises with context
- **Acceptance criteria:**
  - `RAGPipeline.run("What helps with stress?")` returns a `QueryResponse`
  - Response contains `answer`, `sources` (list), and `query_time_ms` (int)
  - Pipeline logs total execution time
- **Status:** [ ] Not Started

---

### T-004: Write unit tests for RAG services
- **Branch:** `feature/SPR-004-T004-tests`
- **Dependencies:** T-001, T-002, T-003
- **Deliverable:**
  - `tests/test_retriever.py`:
    - Test `embed()` returns list of 384 floats
    - Test `search()` with a populated test repo returns HerbChunks
    - Test `search()` with empty repo returns empty list
    - Use real `sentence-transformers` model (it's local, no API cost)
    - Use temp directory for ChromaDB (same pattern as test_herb_repository.py)
  - `tests/test_generator.py`:
    - **Mock the Anthropic API** — no real Claude calls in tests
    - Test prompt construction: verify the formatted prompt includes numbered sources matching BLU-002 §4
    - Test `synthesize()` with mocked API response returns answer text
    - Test `synthesize()` with empty chunks returns "No relevant sources found" without API call
    - Test API error handling (mocked 500, rate limit)
  - `tests/test_pipeline.py`:
    - Mock both retriever and generator
    - Test `run()` returns a `QueryResponse` with correct structure
    - Test `query_time_ms` is a positive integer
    - Test pipeline handles retriever failure gracefully
  - All tests use fake API key
- **Acceptance criteria:**
  - `pytest tests/ -v` passes ALL tests (SPR-001 + SPR-002 + SPR-004)
  - Minimum 10 new test functions
  - No test makes a real Anthropic API call
  - Retriever tests may use the real sentence-transformers model (local, free)
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 RetrieverService | Developer B | [ ] | `feature/SPR-004-T001-retriever` | [ ] |
| T-002 GeneratorService | Developer B | [ ] | `feature/SPR-004-T002-generator` | [ ] |
| T-003 RAGPipeline | Developer B | [ ] | `feature/SPR-004-T003-pipeline` | [ ] |
| T-004 Unit tests | Developer B | [ ] | `feature/SPR-004-T004-tests` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

- [ ] All 4 tasks pass their acceptance criteria
- [ ] `RetrieverService.embed()` returns 384-dimensional vector
- [ ] `GeneratorService.synthesize()` builds BLU-002 §4 prompt correctly
- [ ] `RAGPipeline.run()` returns a complete `QueryResponse`
- [ ] `pytest tests/ -v` passes ALL tests
- [ ] No real Anthropic API calls in tests
- [ ] No files modified outside `backend/rag/` and sprint-specific test files
- [ ] No hardcoded secrets
- [ ] All GOV compliance requirements met
- [ ] No open `DEF-` reports against this sprint

---

## Audit Notes (Architect)

[Architect fills this in after Developer submits for review.]

**Verdict:** PENDING
**Deploy approved:** NO — pending audit
