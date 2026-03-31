---
id: SPR-002
title: "Phase 2 — Domain Model + Repository Layer"
type: how-to
status: ACTIVE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, domain-model, repository, chromadb]
related: [SPR-001, PRJ-001, BLU-001, BLU-002]
created: 2026-03-31
updated: 2026-03-31
version: 1.0.0
---

> **BLUF:** Sprint 002 builds the data foundation — the `HerbChunk` domain model, the `HerbRepository` wrapping ChromaDB, and the Pydantic response schemas. 5 tasks assigned to Developer Agent. Exit criterion: `HerbRepository.add()` → `HerbRepository.search()` round-trip returns correct chunks from a persistent ChromaDB collection, verified by unit tests. **Governance compliance is mandatory from task one.**

# Sprint 002: Phase 2 — Domain Model + Repository Layer

**Phase:** 2 — Domain + Repository
**Target:** Scope-bounded (AI-agent pace)
**Agent(s):** Backend Developer
**Dependencies:** SPR-001 (scaffold must be merged to `master`)
**Blueprints:** BLU-001 §4 (directory structure), BLU-001 §5 (layer contracts), BLU-002 §3 (retrieval), BLU-002 §6 (HerbChunk model)

---

## ⚠️ Mandatory Compliance — Every Task

> All tasks in this sprint MUST incorporate these governance standards. They are not optional and not deferred.

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | Every new `.md` file requires valid YAML frontmatter. Referential integrity: every doc ID referenced must exist (§12.1). |
| **GOV-002** | Unit tests for every new module — `test_herb_chunk.py`, `test_herb_repository.py`, `test_schemas.py`. |
| **GOV-003** | Python: type annotations on every function. Max 60 lines per function. Docstrings on every public function and class. No `# type: ignore`. |
| **GOV-004** | `HerbRepository` methods must raise typed exceptions (not bare `Exception`) on ChromaDB failures. Clear error messages. |
| **GOV-005** | Branch per task: `feature/SPR-002-TNNN-description`. Commit format: `feat(SPR-002): T-NNN description`. Do NOT push to `master`. |
| **GOV-006** | `HerbRepository` must log: collection initialization, add operations (count), search operations (query, result count, latency). Use `structlog`. |
| **GOV-007** | Update task status in this sprint doc as you work. If blocked, file a `DEF-` doc and notify Architect. |
| **GOV-008** | No new dependencies required — all packages are in `requirements.txt` from SPR-001. |

**Acceptance gate:** No task is considered complete unless ALL applicable governance requirements are met.

---

## Developer Agent Tasks

### T-001: Create `backend/models/herb_chunk.py` — Domain Model
- **Branch:** `feature/SPR-002-T001-herb-chunk-model`
- **Dependencies:** None
- **Blueprints:** BLU-002 §6
- **Deliverable:**
  - `backend/models/herb_chunk.py` — Python `dataclass`
  - Fields (all required, exact names):
    ```python
    @dataclass
    class HerbChunk:
        id: str              # Format: "{source_type}-{identifier}-chunk-{index}"
        text: str            # The actual text excerpt (up to ~512 tokens)
        source_type: str     # Literal: "PubMed" | "MSK" | "USDA Duke" | "WHO"
        title: str           # Document or article title
        url: str             # Direct link to source
        year: str            # Publication year (string, not int — some sources lack year)
        herbs: list[str]     # Herb names mentioned in this chunk
        chunk_index: int     # Position within the original document
    ```
  - Methods:
    - `to_source() -> dict` — returns a dict with keys: `source_type`, `title`, `url`, `year`, `excerpt` (first 300 chars of `text`)
    - `to_chroma_metadata() -> dict` — returns metadata dict suitable for ChromaDB storage (all fields except `text`, with `herbs` joined as comma-separated string since ChromaDB metadata values must be str/int/float)
    - `@classmethod from_chroma(cls, id: str, document: str, metadata: dict) -> HerbChunk` — reconstructs a HerbChunk from ChromaDB query results
  - Full docstrings on the class and all methods
  - Type annotations everywhere
- **Acceptance criteria:**
  - `from backend.models.herb_chunk import HerbChunk` succeeds
  - `HerbChunk` round-trips through `to_chroma_metadata()` → `from_chroma()` without data loss
  - `to_source()` truncates text to 300 chars for the excerpt
- **Status:** [ ] Not Started

---

### T-002: Create `backend/api/schemas/responses.py` — Response Schemas
- **Branch:** `feature/SPR-002-T002-response-schemas`
- **Dependencies:** T-001
- **Blueprints:** BLU-002 §5 (response schema)
- **Deliverable:**
  - `backend/api/schemas/responses.py` — Pydantic `BaseModel` classes
  - Classes:
    ```python
    class Source(BaseModel):
        source_type: str   # "PubMed" | "MSK" | "USDA Duke" | "WHO"
        title: str
        url: str
        year: str
        excerpt: str       # First 300 chars of chunk text

    class QueryResponse(BaseModel):
        answer: str
        sources: list[Source]
        query_time_ms: int

    class StatusResponse(BaseModel):
        status: str        # "ok"
        service: str       # "herbalism-rag"
        version: str
        doc_count: int
    ```
  - **Also update** `backend/main.py` to use `StatusResponse` as the `response_model` for `GET /api/status` instead of returning a raw dict
  - Full docstrings on all classes
- **Acceptance criteria:**
  - `from backend.api.schemas.responses import Source, QueryResponse, StatusResponse` succeeds
  - `StatusResponse` can serialize the current status route output
  - Existing `test_status.py` tests still pass after the `main.py` update
- **Status:** [ ] Not Started

---

### T-003: Create `backend/api/schemas/requests.py` — Request Schemas
- **Branch:** `feature/SPR-002-T003-request-schemas`
- **Dependencies:** None
- **Blueprints:** BLU-002 §5
- **Deliverable:**
  - `backend/api/schemas/requests.py` — Pydantic `BaseModel`
  - Class:
    ```python
    class QueryRequest(BaseModel):
        question: str  # Min length 3, max length 1000

        @field_validator("question")
        @classmethod
        def question_must_not_be_blank(cls, v: str) -> str:
            if not v.strip():
                raise ValueError("Question must not be blank")
            return v.strip()
    ```
  - Validates: non-empty, stripped whitespace, reasonable length bounds
  - Full docstring
- **Acceptance criteria:**
  - `QueryRequest(question="What helps with stress?")` succeeds
  - `QueryRequest(question="")` raises `ValidationError`
  - `QueryRequest(question="  ")` raises `ValidationError`
- **Status:** [ ] Not Started

---

### T-004: Create `backend/db/herb_repository.py` — Repository Layer
- **Branch:** `feature/SPR-002-T004-herb-repository`
- **Dependencies:** T-001
- **Blueprints:** BLU-001 §5 (repository contract), BLU-002 §3 (retrieval)
- **Deliverable:**
  - `backend/db/herb_repository.py` — `HerbRepository` class
  - **Constructor**: accepts `settings` (or reads from `backend.config.settings`). Initializes:
    - ChromaDB `PersistentClient` at `settings.chroma_db_path`
    - Gets or creates collection named `settings.collection_name`
    - Logs initialization with `structlog`
  - **Methods**:
    ```python
    def add(self, chunks: list[HerbChunk]) -> int:
        """Add chunks to ChromaDB. Returns count added.
        Stores: id, document (text), metadata (from to_chroma_metadata()).
        Skips duplicates by ID (upsert behavior).
        Logs: count added, time taken."""

    def search(self, query_embedding: list[float], n: int = 8) -> list[HerbChunk]:
        """Search by embedding vector. Returns top-n HerbChunks.
        Uses ChromaDB collection.query().
        Logs: result count, time taken."""

    def list_herbs(self) -> list[str]:
        """Return sorted, unique list of all herb names in the collection.
        Queries all metadata, extracts herbs field, deduplicates."""

    def stats(self) -> dict:
        """Return {doc_count: int, sources: dict[str, int]}.
        doc_count = total chunks. sources = count per source_type."""
    ```
  - All methods must:
    - Have full docstrings with Args/Returns/Raises
    - Use type annotations
    - Log operations via `structlog`
    - Handle ChromaDB exceptions and re-raise as descriptive errors
    - Stay under 60 lines each
- **Acceptance criteria:**
  - `HerbRepository` instantiates and creates a ChromaDB collection at `data/chroma_db/`
  - `add()` stores chunks that survive process restart (persistent)
  - `search()` returns `HerbChunk` objects with all metadata intact
  - `stats()` returns correct counts
  - `list_herbs()` returns deduplicated, sorted herb names
- **Status:** [ ] Not Started

---

### T-005: Write Unit Tests for Domain Model and Repository
- **Branch:** `feature/SPR-002-T005-tests`
- **Dependencies:** T-001, T-002, T-003, T-004
- **Blueprints:** None (GOV-002 testing protocol)
- **Deliverable:**
  - `tests/test_herb_chunk.py`:
    - Test `HerbChunk` construction with valid data
    - Test `to_source()` returns correct dict with 300-char excerpt truncation
    - Test `to_chroma_metadata()` serializes herbs as comma-separated string
    - Test `from_chroma()` reconstructs HerbChunk correctly (round-trip)
  - `tests/test_schemas.py`:
    - Test `Source`, `QueryResponse`, `StatusResponse` serialize correctly
    - Test `QueryRequest` validation: valid input, empty string, whitespace-only, too long
  - `tests/test_herb_repository.py`:
    - Use a **temporary directory** for ChromaDB (not the real `data/chroma_db/`)
    - Test `add()` + `search()` round-trip: add 3 chunks, search, verify results contain the added chunks
    - Test `stats()` returns correct `doc_count` and `sources` breakdown
    - Test `list_herbs()` returns deduplicated, sorted names
    - Test `add()` with duplicate IDs does not create duplicate entries (upsert)
    - Test `search()` with no results returns empty list
  - All tests use fake API key (same pattern as `test_status.py`)
  - All tests have docstrings
- **Acceptance criteria:**
  - `pytest tests/ -v` passes ALL tests (including the existing test_status.py)
  - Repository tests use temp directory, not the real data dir
  - No tests make real API calls
  - Minimum 10 test functions across the 3 test files
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 HerbChunk model | Developer | [ ] | `feature/SPR-002-T001-herb-chunk-model` | [ ] |
| T-002 Response schemas | Developer | [ ] | `feature/SPR-002-T002-response-schemas` | [ ] |
| T-003 Request schemas | Developer | [ ] | `feature/SPR-002-T003-request-schemas` | [ ] |
| T-004 HerbRepository | Developer | [ ] | `feature/SPR-002-T004-herb-repository` | [ ] |
| T-005 Unit tests | Developer | [ ] | `feature/SPR-002-T005-tests` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

> The Architect will not close this sprint and will not approve the merge to `master` until every item below is checked.

- [ ] All 5 tasks pass their acceptance criteria
- [ ] `HerbChunk` round-trips through ChromaDB without data loss
- [ ] `HerbRepository.add()` + `search()` round-trip works in tests
- [ ] `pytest tests/ -v` passes ALL tests (including SPR-001 tests)
- [ ] Repository tests use temp directory, not real `data/chroma_db/`
- [ ] No hardcoded secrets
- [ ] All GOV-001 through GOV-008 compliance requirements met
- [ ] No open `DEF-` reports against this sprint

---

## Audit Notes (Architect)

[Architect fills this in after Developer submits for review.]

**Verdict:** PENDING
**Deploy approved:** NO — pending audit
