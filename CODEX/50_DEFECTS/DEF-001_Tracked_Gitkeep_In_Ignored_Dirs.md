---
id: DEF-001
title: "Tracked .gitkeep files inside gitignored directories"
type: reference
status: OPEN
owner: architect
agents: [coder]
tags: [defect, git, scaffold]
related: [SPR-001]
created: 2026-03-31
updated: 2026-03-31
version: 1.0.0
---

> **BLUF:** `data/chroma_db/.gitkeep` and `data/usda_duke/.gitkeep` are tracked in git despite their parent directories being listed in `.gitignore`. This happened because T-001 committed the `.gitkeep` files before T-002 added the `.gitignore`. Once a file is tracked, `.gitignore` has no effect on it.

# Defect Report: Tracked .gitkeep in Gitignored Dirs

## 1. Summary

| Field | Value |
|:------|:------|
| **Priority** | P3 |
| **Severity** | 5-NO EFFECT |
| **Status** | OPEN |
| **Discovered By** | Architect Agent (during SPR-001 audit) |
| **Discovered During** | Sprint audit — acceptance criteria verification |
| **Component** | Git configuration |
| **Branch** | `fix/DEF-001-untrack-gitkeep` |

## 2. Steps to Reproduce

1. `cd /home/ubuntu/projects/herbalism_rag_dev`
2. `git check-ignore data/chroma_db/` → no output (expected: `data/chroma_db/`)
3. `git ls-files data/chroma_db/` → outputs `data/chroma_db/.gitkeep` (file is tracked)

**Expected Result**: `data/chroma_db/` and `data/usda_duke/` should be fully gitignored, no files within them tracked.
**Actual Result**: `.gitkeep` sentinel files inside both dirs are tracked, overriding the gitignore rule.

## 3. Evidence

- `.gitignore` line 5: `data/chroma_db/`
- `.gitignore` line 8: `data/usda_duke/`
- `git ls-files data/chroma_db/` returns `data/chroma_db/.gitkeep`
- Root cause: T-001 committed `.gitkeep` files → T-002 added `.gitignore` afterward → already-tracked files are not affected by gitignore

## 4. Root Cause Analysis

1. **Why are the files tracked?** T-001 created and committed `.gitkeep` files in all empty directories.
2. **Why didn't `.gitignore` fix it?** `.gitignore` was added in T-002, after the files were already in the index.
3. **Why didn't the Developer catch it?** The task ordering in SPR-001 put directory creation (T-001) before gitignore (T-002). The sprint design caused the issue — this is an Architect-side gap, not a Developer error.

## 5. Fix

- **Fix description**: Remove the two `.gitkeep` files from the git index (but not from disk) using `git rm --cached`.
- **Files changed**: `data/chroma_db/.gitkeep`, `data/usda_duke/.gitkeep` (removed from index only)
- **Commands**:
  ```bash
  git rm --cached data/chroma_db/.gitkeep data/usda_duke/.gitkeep
  git commit -m "fix(DEF-001): untrack .gitkeep in gitignored data dirs"
  ```
- **Regression test**: `git check-ignore data/chroma_db/` must return `data/chroma_db/` after fix

## 6. Verification

- [ ] `git rm --cached` executed for both files
- [ ] `git check-ignore data/chroma_db/` returns `data/chroma_db/`
- [ ] `git check-ignore data/usda_duke/` returns `data/usda_duke/`
- [ ] No new errors introduced
- [ ] Architect UAT approved
