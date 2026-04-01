---
id: RUN-002
title: "Multi-Workspace Developer Agent Operations"
type: how-to
status: APPROVED
owner: architect
agents: [architect, coder]
tags: [runbook, workflow, multi-agent, workspaces, parallel]
related: [GOV-005, GOV-007, AGT-002]
created: 2026-04-01
updated: 2026-04-01
version: 1.0.0
---

> **BLUF:** This project uses three Git clones of the same repository. The Architect manages docs in `herbalism_rag`. Two Developer Agents execute code in `herbalism_rag_dev` and `herbalism_rag_dev_secondary`. All three share the same remote `origin/master`. This runbook covers the full workflow: setup, assignment, audit, merge, and sync.

# Multi-Workspace Developer Agent Operations

## 1. Workspace Topology

```
/home/ubuntu/projects/
├── herbalism_rag/               ← ARCHITECT workspace (docs, CODEX, governance)
├── herbalism_rag_dev/           ← DEVELOPER A workspace (primary code)
└── herbalism_rag_dev_secondary/ ← DEVELOPER B workspace (secondary code)
```

All three are clones of: `https://github.com/S2Corro/herbalism_rag.git`
All three track `origin/master`.

### Workspace Rules

| Workspace | Who Uses It | What Gets Modified |
|:----------|:------------|:-------------------|
| `herbalism_rag` | Architect Agent | CODEX docs, MANIFEST, governance, sprint specs |
| `herbalism_rag_dev` | Developer Agent A | Application code, tests |
| `herbalism_rag_dev_secondary` | Developer Agent B | Application code, tests (separate feature area) |

> [!CAUTION]
> Developer Agents must NEVER modify `CODEX/` files. The Architect must NEVER modify application code directly — file an EVO or assign a sprint task instead.

---

## 2. Sprint Assignment Workflow

### Step 1: Write the Sprint
Architect creates `CODEX/05_PROJECT/SPR-NNN_*.md` with:
- Task list with branch names
- Acceptance criteria per task
- Parallel execution warnings (if applicable)
- File boundary restrictions

### Step 2: Register in MANIFEST
Add the sprint entry to `CODEX/00_INDEX/MANIFEST.yaml` under `05_PROJECT`.

### Step 3: Commit and Push
```bash
cd /home/ubuntu/projects/herbalism_rag
git add -A && git commit -m "docs(SPR-NNN): add sprint for ..." && git push origin master
```

### Step 4: Boot the Developer Agent
Open a new Antigravity conversation. Paste the boot prompt:

```
You are Developer Agent [A|B] for the Herbalism RAG project.

BEFORE WRITING A SINGLE FILE, run:
  git pull origin master
  git checkout -b feature/SPR-NNN-T001-description

Create a new branch for EACH task (branch names are in SPR-NNN).
Never commit to master.

Your role: CODEX/80_AGENTS/AGT-002_Developer_Agent.md
Your sprint: CODEX/05_PROJECT/SPR-NNN_*.md
Your architecture: CODEX/20_BLUEPRINTS/BLU-001_System_Architecture.md
Your pipeline spec: CODEX/20_BLUEPRINTS/BLU-002_RAG_Pipeline.md
Repo: /home/ubuntu/projects/herbalism_rag_dev[_secondary]

Read AGT-002 and SPR-NNN first. Execute tasks in order.
Commit after each task. Do NOT merge to master.
```

---

## 3. Parallel Execution Rules

When two developers work simultaneously:

1. **Zero file overlap** — each sprint specifies exactly which directories it may touch
2. **Branch from master** — both agents branch from the same master commit
3. **No cross-rebase** — neither developer rebases against the other's branches
4. **Conflicts = stop** — if a developer needs to modify a shared file, they file an `EVO-` doc and halt

### Typical Parallel Pairs
| Agent A | Agent B | Why no conflicts |
|:--------|:--------|:-----------------|
| SPR-003 (Ingestion) | SPR-004 (RAG) | `backend/ingest/` vs `backend/rag/` |
| SPR-005 (Controllers) | SPR-006 (Frontend) | `backend/api/routes/` vs `frontend/` |

---

## 4. Architect Audit Workflow

When a developer reports "done":

### Step 1: Inspect Branches
```bash
cd /home/ubuntu/projects/herbalism_rag_dev  # or _secondary
git fetch --all
git log --oneline master..$(git branch --sort=-committerdate | head -1 | tr -d ' *')
```

### Step 2: Check File Boundaries
```bash
git diff --name-only master..feature/SPR-NNN-TNNN-final-task
```
Verify no files outside the sprint's allowed directories were modified.

### Step 3: Check Parallel Conflicts (if parallel sprint)
```bash
# Generate file lists for both sprints
git diff --name-only master..feature/SPR-A-final > /tmp/a_files.txt
git diff --name-only master..feature/SPR-B-final > /tmp/b_files.txt
comm -12 <(sort /tmp/a_files.txt) <(sort /tmp/b_files.txt)
# Empty output = no conflicts
```

### Step 4: Code Review
- Read each new file (view_file tool)
- Verify: type annotations, docstrings, < 60 LOC functions, structlog, typed exceptions
- Verify: no hardcoded secrets (`grep -rn "sk-ant"`)

### Step 5: Run Tests
```bash
source .venv/bin/activate
PYTHONPATH=$(pwd) pytest tests/ -v --tb=short
```

### Step 6: Merge
```bash
git checkout master
git pull origin master
git merge feature/SPR-NNN-final-task --no-ff -m "merge(SPR-NNN): description — N tests pass, N defects"
git push origin master
```

### Step 7: Sync All Workspaces
```bash
# Architect workspace
cd /home/ubuntu/projects/herbalism_rag && git pull --rebase origin master

# Other dev workspace
cd /home/ubuntu/projects/herbalism_rag_dev[_secondary] && git checkout master && git pull origin master
```

### Step 8: Update MANIFEST
Mark sprint as COMPLETE. Register any DEF- or EVO- docs filed.

---

## 5. Venv Management

Each dev workspace has its own `.venv/`. They can drift.

### Fresh Setup
```bash
cd /home/ubuntu/projects/herbalism_rag_dev
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Known Issue: Venv Staleness
If a sprint modifies `requirements.txt` (e.g., DEF-002 upgraded chromadb), existing venvs become stale. Fix:
```bash
pip install -r requirements.txt --upgrade
```

---

## 6. Defect Filing During Audit

If the architect finds issues:

1. Create `CODEX/50_DEFECTS/DEF-NNN_*.md`
2. Register in MANIFEST
3. Communicate to developer: "Fix DEF-NNN, push to the same branch, report back"
4. After fix: re-audit, verify, merge
