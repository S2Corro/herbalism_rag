---
id: SPR-005
title: "Phase 5 — API Controllers"
type: how-to
status: ACTIVE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, api, controllers, routes, fastapi]
related: [SPR-002, SPR-003, SPR-004, PRJ-001, BLU-001, BLU-002]
created: 2026-04-01
updated: 2026-04-01
version: 1.0.0
---

> **BLUF:** Sprint 005 wires the RAG pipeline and ingestion data to HTTP endpoints — `POST /api/query`, `GET /api/herbs`, and refactors `GET /api/status` to use the real ChromaDB doc count. Exit criterion: all three endpoints return correct responses with proper error handling, verified by integration-style tests using the async test client. **This sprint runs in parallel with SPR-006. Do NOT modify files in `frontend/`.**

# Sprint 005: Phase 5 — API Controllers

**Phase:** 5 — API Controllers
**Target:** Scope-bounded (AI-agent pace)
**Agent(s):** Developer Agent A (API)
**Dependencies:** SPR-002 (schemas), SPR-003 (ingesters), SPR-004 (RAG pipeline) — all on `master`
**Blueprints:** BLU-001 §2 (Controller layer), BLU-001 §5 (layer contracts), BLU-002 §1 (end-to-end), BLU-002 §5 (response schema)

---

## ⚠️ Parallel Execution Warning

> [!CAUTION]
> **This sprint runs in parallel with SPR-006 (Frontend), executed by a different Developer Agent.**
> - You MUST NOT modify any files in `frontend/`.
> - You MAY modify `backend/main.py` (mounting routes, app factory, lifespan).
> - You MAY modify files in `backend/api/routes/` and `backend/api/schemas/`.
> - You MAY add test files `tests/test_query.py`, `tests/test_herbs.py`.
> - If you need changes to `backend/rag/`, `backend/db/`, or `backend/models/`, file an `EVO-` doc and stop.

---

## ⚠️ Mandatory Compliance — Every Task

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | Referential integrity (§12.1). |
| **GOV-002** | Integration tests for every endpoint using `httpx.AsyncClient`. |
| **GOV-003** | Type annotations, docstrings, max 60 LOC per function. |
| **GOV-004** | Endpoints must return proper HTTP error codes (422 for validation, 500 for pipeline failure). |
| **GOV-005** | Branch per task. Commits: `feat(SPR-005): T-NNN description`. |
| **GOV-006** | Controller routes must log: request received, response time. Use `structlog`. |
| **GOV-007** | Update task status as you work. |
| **GOV-008** | No new pip dependencies needed. |

---

## Developer Agent Tasks

### T-001: Create `backend/api/routes/query.py` — POST /api/query
- **Branch:** `feature/SPR-005-T001-query-route`
- **Dependencies:** None (uses SPR-004 pipeline)
- **Blueprints:** BLU-001 §5 (controller contract), BLU-002 §1, §5
- **Deliverable:**
  - `backend/api/routes/query.py` — FastAPI route
  - Route:
    ```python
    router = APIRouter()

    @router.post("/query", response_model=QueryResponse)
    async def query(request: QueryRequest) -> QueryResponse:
        """Execute a RAG query and return cited answer with sources."""
    ```
  - Flow:
    1. Receive `QueryRequest` (Pydantic validates automatically)
    2. Build the RAG pipeline (lazy singleton or constructed per request — your call, but document the choice)
    3. Call `pipeline.run(request.question)`
    4. Return the `QueryResponse`
  - Error handling:
    - `QueryRequest` validation errors → FastAPI auto-returns 422
    - Pipeline failures → catch, log, return HTTP 500 with JSON error body `{"detail": "..."}`
  - Log: question (truncated), response time
  - The pipeline needs `RetrieverService` (needs `HerbRepository`) and `GeneratorService` (needs API key from `config.settings`)
  - Create a dependency or factory function that wires the pipeline together. Put it in `backend/api/routes/query.py` or a new `backend/api/dependencies.py` — your call.
- **Acceptance criteria:**
  - `POST /api/query {"question": "What helps with cortisol?"}` returns a `QueryResponse`
  - Empty/invalid question returns 422
  - Pipeline failure returns 500 with error detail
- **Status:** [ ] Not Started

---

### T-002: Create `backend/api/routes/herbs.py` — GET /api/herbs
- **Branch:** `feature/SPR-005-T002-herbs-route`
- **Dependencies:** None
- **Blueprints:** BLU-001 §5
- **Deliverable:**
  - `backend/api/routes/herbs.py` — FastAPI route
  - Route:
    ```python
    @router.get("/herbs")
    async def list_herbs() -> dict[str, list[str]]:
        """Return sorted, unique list of all indexed herb names."""
    ```
  - Uses `HerbRepository.list_herbs()`
  - Response format: `{"herbs": ["Ashwagandha", "Chamomile", ...]}`
  - Error handling: repository failure → 500 with error detail
- **Acceptance criteria:**
  - `GET /api/herbs` returns `{"herbs": [...]}`
  - Empty collection returns `{"herbs": []}`
- **Status:** [ ] Not Started

---

### T-003: Refactor `backend/main.py` — Mount routes + lifespan wiring
- **Branch:** `feature/SPR-005-T003-mount-routes`
- **Dependencies:** T-001, T-002
- **Deliverable:**
  - Update `backend/main.py`:
    1. Import and mount `query.router` and `herbs.router` under the `/api` prefix
    2. Update the lifespan to initialize shared resources (HerbRepository) at startup
    3. Refactor `GET /api/status` to use the real `HerbRepository.stats()["doc_count"]` instead of hardcoded 0
    4. Store shared dependencies (repository, pipeline) in `app.state` so routes can access them
  - Keep the existing static file mounting for frontend
  - Existing `test_status.py` tests must still pass
- **Acceptance criteria:**
  - `GET /api/status` returns real ChromaDB doc count
  - All routes accessible: `/api/query`, `/api/herbs`, `/api/status`
  - Existing status tests still pass
  - App starts without errors
- **Status:** [ ] Not Started

---

### T-004: Write integration tests
- **Branch:** `feature/SPR-005-T004-tests`
- **Dependencies:** T-001, T-002, T-003
- **Deliverable:**
  - `tests/test_query.py`:
    - Test `POST /api/query` with valid question (mock the GeneratorService to avoid real Claude calls)
    - Test validation: empty question → 422
    - Test validation: question too long → 422
    - Test pipeline error handling → 500 with detail
  - `tests/test_herbs.py`:
    - Test `GET /api/herbs` returns correct format
    - Test with empty collection → `{"herbs": []}`
  - Update `tests/test_status.py` if needed for the refactored status endpoint
  - All tests use fake API key
  - **Mock the Anthropic API** — no real LLM calls
  - Use `httpx.AsyncClient` with `ASGITransport` (same pattern as existing `test_status.py`)
- **Acceptance criteria:**
  - `pytest tests/ -v` passes ALL tests (SPR-001 through SPR-005)
  - Minimum 8 new test functions
  - No real API calls
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 Query route | Developer A | [ ] | `feature/SPR-005-T001-query-route` | [ ] |
| T-002 Herbs route | Developer A | [ ] | `feature/SPR-005-T002-herbs-route` | [ ] |
| T-003 Mount routes | Developer A | [ ] | `feature/SPR-005-T003-mount-routes` | [ ] |
| T-004 Tests | Developer A | [ ] | `feature/SPR-005-T004-tests` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

- [ ] All 4 tasks pass their acceptance criteria
- [ ] `POST /api/query` returns `QueryResponse` with answer + sources
- [ ] `GET /api/herbs` returns herb list
- [ ] `GET /api/status` returns real doc count
- [ ] `pytest tests/ -v` passes ALL tests
- [ ] No real Anthropic API calls in tests
- [ ] No files modified in `frontend/`
- [ ] No hardcoded secrets
- [ ] All GOV compliance requirements met

---

## Audit Notes (Architect)

**Verdict:** PENDING
**Deploy approved:** NO — pending audit
