---
id: EVO-001
title: "Amend BLU-001 Directory Structure — Sprint 001 Implementation Deviations"
type: reference
status: DRAFT
owner: developer
agents: [coder, architect]
tags: [architecture, blueprint-amendment, python, scaffold]
related: [BLU-001, SPR-001]
created: 2026-03-31
updated: 2026-03-31
version: 1.0.0
---

> **BLUF:** During SPR-001 execution, the Developer Agent created three categories of files not specified in BLU-001 §4: Python `__init__.py` package markers, a `pyproject.toml` for tooling config, and a `tests/` directory. All are necessary for a working Python project. BLU-001 §4 should be amended to include them.

# Evolution Proposal: BLU-001 Directory Structure Amendments

## 1. Overview

| Field | Value |
|:------|:------|
| **Priority** | P1 — blocks accurate blueprint-vs-implementation validation |
| **Status** | DRAFT |
| **Requested By** | Developer Agent (discovered gap during SPR-001 execution) |
| **Estimated Scope** | Small (1 file: BLU-001) |

## 2. Problem Statement

BLU-001 §4 ("Full Directory Structure") defines the canonical directory tree. During SPR-001 implementation, three categories of files were created that are **necessary for the project to function** but are **not listed in BLU-001**:

1. **`__init__.py` files** — Python requires these for package imports. Without them, `from backend.config import settings` fails with `ModuleNotFoundError`. 8 files were created:
   - `backend/__init__.py`
   - `backend/api/__init__.py`
   - `backend/api/routes/__init__.py`
   - `backend/api/schemas/__init__.py`
   - `backend/rag/__init__.py`
   - `backend/ingest/__init__.py`
   - `backend/db/__init__.py`
   - `backend/models/__init__.py`

2. **`pyproject.toml`** — Standard Python project configuration file. Currently contains pytest settings (`asyncio_mode = "auto"`, `testpaths`). Required for `pytest` to discover and run async tests correctly. Will also be the natural home for future tool configs (mypy, ruff, black, etc.).

3. **`tests/` directory** — SPR-001 T-006 specifies creating `tests/test_status.py`, but BLU-001 §4 does not include a `tests/` directory in the project tree. The directory exists and contains working tests.

## 3. Proposed Solution

Amend BLU-001 §4 to include all three categories. Proposed additions to the directory tree:

### 3.1 Files to Add to BLU-001 §4

| Action | Path | Purpose |
|:-------|:-----|:--------|
| ADD | `backend/__init__.py` | Python package marker |
| ADD | `backend/api/__init__.py` | Python package marker |
| ADD | `backend/api/routes/__init__.py` | Python package marker |
| ADD | `backend/api/schemas/__init__.py` | Python package marker |
| ADD | `backend/rag/__init__.py` | Python package marker |
| ADD | `backend/ingest/__init__.py` | Python package marker |
| ADD | `backend/db/__init__.py` | Python package marker |
| ADD | `backend/models/__init__.py` | Python package marker |
| ADD | `tests/` | Test directory (referenced by SPR-001 T-006) |
| ADD | `tests/test_status.py` | Unit test example (shows naming convention) |
| ADD | `pyproject.toml` | Python project/tooling configuration |

### 3.2 Proposed Updated Tree (additions marked with ←)

```
herbalism_rag/
|
|- backend/
|   |- __init__.py                  # Package marker  ← NEW
|   |- main.py
|   |- config.py
|   |
|   |- api/
|   |   |- __init__.py             # Package marker  ← NEW
|   |   |- routes/
|   |   |   |- __init__.py         # Package marker  ← NEW
|   |   |   |- query.py
|   |   |   |- herbs.py
|   |   |   |- status.py
|   |   |- schemas/
|   |       |- __init__.py         # Package marker  ← NEW
|   |       |- requests.py
|   |       |- responses.py
|   |
|   |- rag/
|   |   |- __init__.py             # Package marker  ← NEW
|   |   |- pipeline.py
|   |   |- retriever.py
|   |   |- generator.py
|   |
|   |- ingest/
|   |   |- __init__.py             # Package marker  ← NEW
|   |   |- pubmed.py
|   |   |- msk_herbs.py
|   |   |- usda_duke.py
|   |
|   |- db/
|   |   |- __init__.py             # Package marker  ← NEW
|   |   |- herb_repository.py
|   |
|   |- models/
|       |- __init__.py             # Package marker  ← NEW
|       |- herb_chunk.py
|
|- frontend/
|   |- index.html
|   |- css/style.css
|   |- js/app.js
|
|- data/
|   |- chroma_db/
|   |- usda_duke/
|   |- seeds/
|       |- who_monographs.json
|
|- scripts/
|   |- ingest.py
|
|- tests/                           # Test suite  ← NEW
|   |- test_status.py              # Example: test_{module}.py naming  ← NEW
|
|- .env.example
|- .gitignore
|- requirements.txt
|- pyproject.toml                   # Project/tooling config  ← NEW
|- README.md
```

### 3.3 Dependencies

None — these files already exist in the codebase.

## 4. Acceptance Criteria

- [ ] BLU-001 §4 directory tree includes all `__init__.py` files
- [ ] BLU-001 §4 directory tree includes `tests/` with example test file
- [ ] BLU-001 §4 directory tree includes `pyproject.toml`
- [ ] MANIFEST.yaml updated if BLU-001 version changes

## 5. Risks & Open Questions

| Risk / Question | Mitigation / Answer |
|:----------------|:-------------------|
| Should `__init__.py` files be shown in the tree or implied by convention? | Recommend showing them explicitly — removes ambiguity for AI agents that read the tree literally. |
| Should `conftest.py` also be added to `tests/`? | Not yet — no shared fixtures exist. Add when needed in a future sprint. |
| Should `pyproject.toml` replace `requirements.txt` as the dependency manifest? | Not in scope for this proposal. A separate EVO could evaluate migrating to `pyproject.toml` project metadata (PEP 621). |
