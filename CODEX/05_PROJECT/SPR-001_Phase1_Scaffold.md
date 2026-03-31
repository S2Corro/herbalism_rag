---
id: SPR-001
title: "Phase 1 — Project Scaffold"
type: how-to
status: ACTIVE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, scaffold, fastapi, python]
related: [PRJ-001, BLU-001, BLU-002]
created: 2026-03-31
updated: 2026-03-31
version: 1.0.0
---

> **BLUF:** Sprint 001 builds the project skeleton — directory structure, dependency manifest, environment config, and a running FastAPI skeleton. 6 tasks assigned to Developer Agent. Exit criterion: `GET /api/status` returns `{"status": "ok"}` and server boots without error. **Governance compliance is mandatory from task one.**

# Sprint 001: Phase 1 — Project Scaffold

**Phase:** 1 — Scaffold
**Target:** Scope-bounded (AI-agent pace)
**Agent(s):** Backend Developer
**Dependencies:** None (first sprint)
**Contracts:** None yet defined — this sprint creates the contracts-ready structure
**Blueprints:** BLU-001 §Directory Structure, BLU-001 §Tech Stack

---

## ⚠️ Mandatory Compliance — Every Task

> All tasks in this sprint MUST incorporate these governance standards. They are not optional and not deferred.

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | Every `.md` file you create requires valid YAML frontmatter. No doc without it. |
| **GOV-002** | Unit test for `GET /api/status` must be written alongside the route (T-006). |
| **GOV-003** | Python: type annotations on every function signature. Max 60 lines per function. Docstrings on every public function. No `# type: ignore`. |
| **GOV-004** | `config.py` must raise a clear, typed `ConfigurationError` on startup if `ANTHROPIC_API_KEY` is missing. No silent `None`. |
| **GOV-005** | Branch per task: `feature/SPR-001-TNNN-description`. Commit format: `feat(SPR-001): T-NNN description`. Do NOT push to `master`. |
| **GOV-006** | `main.py` startup sequence must emit one structured JSON log line: `{"event": "startup", "status": "ok", "doc_count": 0}`. Use Python `structlog` or `logging` with JSON formatter. |
| **GOV-007** | Update task status in this sprint doc as you work. If blocked, file a `DEF-` doc and notify Architect. |
| **GOV-008** | `.gitignore` must exclude: `.env`, `data/chroma_db/`, `data/usda_duke/`, `__pycache__/`, `*.pyc`, `.venv/`. |

**Acceptance gate:** No task is considered complete unless ALL applicable governance requirements are met.

---

## Developer Agent Tasks

### T-001: Create Directory Structure
- **Branch:** `feature/SPR-001-T001-directory-structure`
- **Dependencies:** None
- **Contracts:** None
- **Blueprints:** BLU-001 §Full Project Structure
- **Deliverable:**
  - Create the full directory tree as specified in BLU-001
  - Every directory that contains no files yet gets a `.gitkeep` placeholder
  - Top-level directories: `backend/`, `frontend/`, `data/`, `scripts/`
  - `backend/` subdirs: `api/routes/`, `api/schemas/`, `rag/`, `ingest/`, `db/`, `models/`
  - `frontend/` subdirs: `css/`, `js/`
  - `data/` subdirs: `chroma_db/`, `usda_duke/`, `seeds/`
- **Acceptance criteria:**
  - `find . -type d` output matches BLU-001 directory spec exactly
  - All empty directories contain `.gitkeep`
- **Status:** [ ] Not Started

---

### T-002: Create `.gitignore` and `.env.example`
- **Branch:** `feature/SPR-001-T002-gitignore-env`
- **Dependencies:** T-001
- **Contracts:** None
- **Blueprints:** BLU-001 §Security
- **Deliverable:**
  - `.gitignore` at project root — must exclude: `.env`, `data/chroma_db/`, `data/usda_duke/`, `__pycache__/`, `*.pyc`, `.venv/`, `*.egg-info/`, `dist/`, `.pytest_cache/`, `.mypy_cache/`
  - `.env.example` at project root — single line: `ANTHROPIC_API_KEY=your-anthropic-api-key-here`
  - A comment block in `.env.example` explaining: (1) copy to `.env`, (2) never commit `.env`, (3) get key from console.anthropic.com
- **Acceptance criteria:**
  - `git check-ignore .env` returns `.env` (file is gitignored)
  - `git check-ignore data/chroma_db/` returns the path (gitignored)
  - `.env.example` is tracked by git (not gitignored)
  - `.env.example` contains only a placeholder value, never a real key
- **Status:** [ ] Not Started

---

### T-003: Create `requirements.txt`
- **Branch:** `feature/SPR-001-T003-requirements`
- **Dependencies:** T-001
- **Contracts:** None
- **Blueprints:** BLU-001 §Tech Stack, BLU-002 §Embeddings
- **Deliverable:**
  - `requirements.txt` at project root with the following pinned dependencies:

  ```
  # Web framework
  fastapi==0.115.6
  uvicorn[standard]==0.32.1

  # Configuration
  pydantic-settings==2.7.0

  # Vector store
  chromadb==0.5.23

  # Embeddings (local, no API cost)
  sentence-transformers==3.3.1

  # LLM
  anthropic==0.42.0

  # HTTP client (for ingesters)
  httpx==0.28.1
  beautifulsoup4==4.12.3

  # Logging
  structlog==24.4.0

  # Testing
  pytest==8.3.4
  pytest-asyncio==0.24.0
  httpx==0.28.1
  ```

  - Comments grouping dependencies by purpose (as shown above)
- **Acceptance criteria:**
  - `pip install -r requirements.txt` completes without errors in a clean venv
  - No unpinned packages (all have `==` version pins)
- **Status:** [ ] Not Started

---

### T-004: Create `backend/config.py`
- **Branch:** `feature/SPR-001-T004-config`
- **Dependencies:** T-003
- **Contracts:** None
- **Blueprints:** BLU-001 §Security
- **Deliverable:**
  - `backend/config.py` using `pydantic-settings` `BaseSettings`
  - Settings class must expose:
    - `anthropic_api_key: str` — read from env var `ANTHROPIC_API_KEY`
    - `chroma_db_path: str` — defaults to `"data/chroma_db"`
    - `collection_name: str` — defaults to `"herbalism"`
    - `embedding_model: str` — defaults to `"sentence-transformers/all-MiniLM-L6-v2"`
    - `llm_model: str` — defaults to `"claude-haiku-20240307"`
    - `top_k: int` — defaults to `8`
  - On instantiation, if `ANTHROPIC_API_KEY` is missing or empty, raise a `ValueError` with message: `"ANTHROPIC_API_KEY is required. Copy .env.example to .env and add your key."`
  - Module-level singleton: `settings = Settings()`
  - Full docstring on the class explaining it reads from `.env` via `pydantic-settings`
  - Type annotations on every field
- **Acceptance criteria:**
  - `python -c "from backend.config import settings"` succeeds when `.env` has a valid key
  - `python -c "from backend.config import settings"` raises `ValueError` with the specified message when key is absent
  - Module has no hardcoded secrets
- **Status:** [ ] Not Started

---

### T-005: Create `backend/main.py` — FastAPI App Factory
- **Branch:** `feature/SPR-001-T005-main`
- **Dependencies:** T-004
- **Contracts:** None
- **Blueprints:** BLU-001 §Controller Layer
- **Deliverable:**
  - `backend/main.py` — FastAPI application factory
  - App must:
    1. Import and call `settings` from `config.py` (fails fast on missing key)
    2. Mount `frontend/` directory as StaticFiles at `/` with `html=True`
    3. Register an API router under prefix `/api` (router can be a placeholder that only has the status route for now)
    4. Include a `/api/status` GET route (may be inline for now, or imported from `api/routes/status.py`)
    5. On startup: emit one structured JSON log line via `structlog` or `logging.getLogger`:
       ```json
       {"event": "startup", "status": "ok", "service": "herbalism-rag", "doc_count": 0}
       ```
    6. Include basic CORS middleware allowing all origins (dev convenience; production tightening is Phase 7)
  - `GET /api/status` returns:
    ```json
    {"status": "ok", "service": "herbalism-rag", "version": "0.1.0", "doc_count": 0}
    ```
  - Docstring on the module explaining the app factory pattern
  - Type annotations where applicable
- **Acceptance criteria:**
  - `uvicorn backend.main:app --reload` starts without errors
  - `curl http://localhost:8000/api/status` returns the specified JSON
  - Startup log line is emitted to stdout in JSON format
  - Static file mounting does not crash even if `frontend/` only has a `.gitkeep`
- **Status:** [ ] Not Started

---

### T-006: Write Unit Test for `GET /api/status`
- **Branch:** `feature/SPR-001-T006-tests`
- **Dependencies:** T-005
- **Contracts:** None
- **Blueprints:** BLU-001 §API Design
- **Deliverable:**
  - `tests/test_status.py` — unit test using `httpx.AsyncClient` + FastAPI `TestClient` or `pytest-asyncio`
  - Test must verify:
    1. `GET /api/status` returns HTTP 200
    2. Response body contains `"status": "ok"`
    3. Response body contains `"service": "herbalism-rag"`
    4. Response `Content-Type` is `application/json`
  - Test file has YAML frontmatter block as a Python comment at the top (per GOV-001 spirit — a brief header comment with doc title, sprint, and author)
  - Test uses a test `.env` with a fake API key so it doesn't require a real Anthropic key to pass
- **Acceptance criteria:**
  - `pytest tests/test_status.py -v` passes with all tests GREEN
  - Test does not make real HTTP calls to Anthropic (it only tests the status route)
  - Coverage for `main.py` status route is 100%
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 Directory Structure | Developer | [ ] | `feature/SPR-001-T001-directory-structure` | [ ] |
| T-002 .gitignore + .env.example | Developer | [ ] | `feature/SPR-001-T002-gitignore-env` | [ ] |
| T-003 requirements.txt | Developer | [ ] | `feature/SPR-001-T003-requirements` | [ ] |
| T-004 config.py | Developer | [ ] | `feature/SPR-001-T004-config` | [ ] |
| T-005 main.py + status route | Developer | [ ] | `feature/SPR-001-T005-main` | [ ] |
| T-006 Unit test | Developer | [ ] | `feature/SPR-001-T006-tests` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

> The Architect will not close this sprint and will not approve the PR to `master` until every item below is checked.

- [ ] All 6 tasks pass their acceptance criteria
- [ ] `uvicorn backend.main:app --reload` starts without errors
- [ ] `GET /api/status` returns `{"status": "ok", ...}`
- [ ] `pytest tests/test_status.py -v` passes with all GREEN
- [ ] `.env` is confirmed gitignored (`git check-ignore .env` returns `.env`)
- [ ] No hardcoded secrets anywhere in the codebase
- [ ] All GOV-001 through GOV-008 compliance requirements met (Architect spot-check)
- [ ] No open `DEF-` reports against this sprint

---

## Audit Notes (Architect)

[Architect fills this in after Developer submits for review.]

**Verdict:** PENDING
**Deploy approved:** NO — pending audit
