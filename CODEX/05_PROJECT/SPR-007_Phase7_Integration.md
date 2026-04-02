---
id: SPR-007
title: "Phase 7 — Integration & Verification"
type: how-to
status: ACTIVE
owner: architect
agents: [architect, tester]
tags: [project-management, sprint, integration, verification, final]
related: [SPR-005, SPR-006, PRJ-001, BLU-001, BLU-002]
created: 2026-04-01
updated: 2026-04-01
version: 1.0.0
---

> **BLUF:** Final sprint — populate the knowledge base, boot the full stack, verify 10 end-to-end queries through the browser, clean up code, and capture a demo. Exit criterion: the app works end-to-end with real data, all tests pass, and GitHub has the final push.

# Sprint 007: Phase 7 — Integration & Verification

**Phase:** 7 — Integration & Verification
**Target:** Scope-bounded
**Agent(s):** Architect (verification)
**Dependencies:** SPR-005 + SPR-006 merged to master

---

## Tasks

### T-001: Run full test suite
- Verify all 92+ tests pass on master with merged SPR-005 + SPR-006 code

### T-002: Populate ChromaDB via ingestion
- Run `scripts/ingest.py` to load WHO seed data + any available sources
- Verify doc count > 0 via `GET /api/status`

### T-003: Boot full stack and browser verification
- Start `uvicorn backend.main:app`
- Open browser, verify frontend loads
- Test 10 end-to-end queries through the UI
- Verify citations render, source cards expand, herb index loads

### T-004: Code cleanup
- Remove commented mock block in `frontend/js/app.js` (lines 704-738)
- Any other minor cleanup

### T-005: Final push and demo capture
- Commit cleanup, push to GitHub
- Screenshot or recording of working app

---

## Sprint Completion Criteria

- [ ] All tests pass
- [ ] ChromaDB populated with real data
- [ ] 10 queries tested end-to-end in browser
- [ ] No console errors in browser
- [ ] Final code pushed to GitHub
