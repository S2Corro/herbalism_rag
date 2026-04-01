---
id: DEF-002
title: "ChromaDB version pin mismatch — 0.5.23 breaks upsert without embeddings"
type: reference
status: VERIFIED
owner: architect
agents: [coder]
tags: [defect, dependency, chromadb]
related: [SPR-002, SPR-004]
created: 2026-04-01
updated: 2026-04-01
version: 1.0.0
---

> **BLUF:** `requirements.txt` pinned ChromaDB at 0.5.23, but Agent A's workspace auto-installed 1.5.5. The 0.5.23 version requires embeddings when calling `upsert()` on a collection with `embedding_function=None`, causing 5 test failures in SPR-004's workspace. Upgrading the pin to 1.5.5 fixes all failures. Fix applied to `requirements.txt`.

# Defect Report: ChromaDB Version Pin Mismatch

## 1. Summary

| Field | Value |
|:------|:------|
| **Priority** | P1 |
| **Severity** | 3-MAJOR |
| **Status** | VERIFIED |
| **Discovered By** | Developer Agent A (flagged), confirmed by Architect during SPR-003/004 audit |
| **Discovered During** | SPR-004 test execution |
| **Component** | `requirements.txt`, `backend/db/herb_repository.py` |
| **Branch** | Fixed in architect workspace (direct to `master` — config-only) |

## 2. Steps to Reproduce

1. Install dependencies with `pip install -r requirements.txt` (installs chromadb==0.5.23)
2. Run `pytest tests/test_herb_repository.py -v`
3. 5 tests fail with: `ValueError: You must provide an embedding function to compute embeddings`

**Expected Result**: All repository tests pass.
**Actual Result**: `upsert()` fails because ChromaDB 0.5.23 requires either embeddings or an embedding function.

## 3. Evidence

- Agent B workspace (chromadb==0.5.23): 5 FAILED, 46 passed
- Agent A workspace (chromadb==1.5.5): 43 passed, 0 failed
- After upgrading Agent B to 1.5.5: 51 passed, 0 failed

## 4. Root Cause Analysis

1. SPR-001 pinned `chromadb==0.5.23` in `requirements.txt`
2. SPR-002 created `HerbRepository` with `embedding_function=None` — correct per our design (we provide raw vectors via RetrieverService)
3. Agent A's venv drifted to 1.5.5 (likely a transitive dependency upgrade)
4. ChromaDB 0.5.23 has a stricter API that requires embeddings on every `upsert()` call when no embedding function is set
5. ChromaDB 1.5.5 handles `upsert()` with documents-only correctly when `embedding_function=None`

## 5. Fix

- **Fix description**: Update `requirements.txt` pin from `chromadb==0.5.23` to `chromadb==1.5.5`
- **Files changed**: `requirements.txt`
- **Regression test**: Existing `tests/test_herb_repository.py` (all 7 tests pass on 1.5.5)

## 6. Verification

- [x] Pin updated to chromadb==1.5.5
- [x] All 51 tests pass on both workspaces
- [x] No new errors introduced
- [x] Architect UAT approved — 2026-04-01
