---
id: DEF-003
title: "Ingestion pipeline crashes with ChromaDB DuplicateIDError on repeated PubMed PMIDs"
type: reference
status: VERIFIED
owner: architect
agents: [coder]
tags: [defect, ingestion, pubmed, chromadb]
related: [SPR-003, SPR-007]t
created: 2026-04-02t
updated: 2026-04-02
version: 1.0.0
---

> **BLUF:** `scripts/ingest.py` crashes with `chromadb.errors.DuplicateIDError` during the final `repo.add()` call because PubMed returns the same article (PMID) for multiple herb search queries, producing identical chunk IDs in a single upsert batch. The batch-level deduplication step is missing entirely.

# Defect Report: Ingest Duplicate PubMed Chunk IDs

## 1. Summary

| Field | Value |
|:------|:------|
| **Priority** | P1 |
| **Severity** | 2-BLOCKING |
| **Status** | VERIFIED |
| **Discovered By** | Human operator (during SPR-007 T-002) |
| **Discovered During** | First live run of `scripts/ingest.py` |
| **Component** | `scripts/ingest.py` — ingestion orchestrator |
| **Branch** | `fix/DEF-003-ingest-deduplicate-chunks` |

## 2. Steps to Reproduce

```bash
cd ~/projects/herbalism_rag
source .venv/bin/activate
python scripts/ingest.py
```

**Expected Result**: All chunks stored in ChromaDB; ingestion completes successfully.

**Actual Result**: Crash at `repo.add(all_chunks)` with:

```
chromadb.errors.DuplicateIDError: Expected IDs to be unique,
found duplicates of: pubmed-41919431-chunk-0 in upsert.
RuntimeError: Failed to add 46 chunks to ChromaDB: ...
```

## 3. Root Cause Analysis

The PubMed ingester (`backend/ingest/pubmed.py`) generates chunk IDs as:

```python
id=f"pubmed-{article['pmid']}-chunk-{i}"
```

The orchestrator (`scripts/ingest.py`) queries PubMed once per herb in `_DEFAULT_HERBS` (10 herbs). A single article frequently appears in search results for multiple herbs (e.g. PMID `41919431` appears for both "Turmeric" and "Ginger"). Each occurrence produces the same chunk ID.

`all_chunks` accumulates one `HerbChunk` per occurrence. When the orchestrator calls `repo.add(all_chunks)`, ChromaDB's `upsert` receives the same ID multiple times **within a single batch call** — which it explicitly rejects. (ChromaDB *tolerates* the same ID across separate `upsert` calls but not within one.)

The fix is to deduplicate `all_chunks` by `chunk.id` before the `repo.add()` call. When duplicates exist, the **last** occurrence is kept (dict comprehension semantics). This is functionally equivalent to first-wins because identical PMIDs produce identical content — the herb query that triggered the hit differs, but the article text is the same.

## 4. Evidence

- `DuplicateIDError` traceback from live run (reproduced above)
- `PubMedIngestor._articles_to_chunks` in `backend/ingest/pubmed.py:233` — ID scheme
- `scripts/ingest.py:127` — `repo.add(all_chunks)` with no prior deduplication

## 5. Fix Specification

**File:** `scripts/ingest.py`

After all four ingesters have run and before `repo.add()`, insert:

```python
# Deduplicate by chunk ID — the same PMID can appear for multiple herbs,
# producing identical IDs in a single batch and causing ChromaDB's
# DuplicateIDError. Dict preserves insertion order (Python 3.7+).
unique_chunks: list[HerbChunk] = list(
    {chunk.id: chunk for chunk in all_chunks}.values()
)
duplicate_count: int = len(all_chunks) - len(unique_chunks)
if duplicate_count:
    logger.warning("ingest_duplicates_removed", count=duplicate_count)
```

Then pass `unique_chunks` (not `all_chunks`) to `repo.add()` and the final log.

**⚠️ Note:** The Architect Agent incorrectly applied this fix directly during the debugging session before this DEF was filed. The developer's job is to:
1. Verify the patch in `scripts/ingest.py` is correct and complete
2. Write a unit test covering the deduplication behaviour
3. Run the full test suite and confirm no regressions
4. Run the live ingestion pipeline end-to-end and confirm success

## 6. Required Unit Test

Add to `tests/test_ingest.py` (or appropriate test file):

- **Scenario:** Provide two `HerbChunk` objects with the same `id`
- **Assert:** After deduplication, only one chunk remains
- **Scenario:** Provide chunks where all IDs are unique
- **Assert:** All chunks are preserved unchanged
- **Scenario:** Empty list input
- **Assert:** No error; result is empty list

## 7. Verification Checklist

- [ ] Patch in `scripts/ingest.py` reviewed and confirmed correct
- [ ] Unit test added and passes
- [ ] `python -m pytest` — full suite passes (92+ tests)
- [ ] `python scripts/ingest.py` runs to completion without error
- [ ] `GET /api/status` returns `doc_count > 0`
- [ ] Commit: `fix(DEF-003): deduplicate ingest chunks before ChromaDB upsert`
- [ ] Architect audit sign-off
