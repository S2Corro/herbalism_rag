---
id: PRJ-001
title: "Herbalism RAG — Project Roadmap"
type: explanation
status: APPROVED
owner: human
agents: [all]
created: 2026-03-31
updated: 2026-04-01
version: 2.0.0
---

> **BLUF:** Herbalism RAG answers natural language herbalism questions using evidence from PubMed, MSK, USDA Duke, and WHO — every answer is cited. Phases 1–4 are COMPLETE. Phases 5–6 are in parallel execution. Phase 7 (Integration) will close the project.

# Herbalism RAG — Project Roadmap

## 1. Vision
Natural language interface over credible herbalism sources. Every answer grounded in retrieved evidence with clickable source citations.

## 2. Guiding Principles
- Credibility first: LLM synthesizes retrieved evidence, does not invent
- Full transparency: every response shows sources with URLs
- Privacy by design: Anthropic key never leaves the server
- Clean architecture: modular monolith, Controller/Service/Repository
- Beauty matters: dark botanical UI, not an MVP

## 3. Scope — In Scope
- Natural language query interface
- RAG pipeline: local embeddings, ChromaDB, Claude Haiku synthesis
- Four ingesters: PubMed, MSK About Herbs, USDA Duke DB, WHO
- Source citation cards on every response
- Botanical web UI served by FastAPI

## 4. Delivery Phases

### Phase 1: Scaffold ✅ COMPLETE (SPR-001)
FastAPI starts, GET /api/status returns ok, .env wired, gitignore set.
- **Delivered:** 2026-03-31
- **Tests:** 6

### Phase 2: Domain + Repository ✅ COMPLETE (SPR-002)
HerbRepository add/search round-trip works, ChromaDB persists to disk.
- **Delivered:** 2026-03-31
- **Tests:** 23 new (29 total)
- **Defects:** DEF-001 (gitkeep tracking — fixed)

### Phase 3: Ingestion Services ✅ COMPLETE (SPR-003)
scripts/ingest.py populates 500+ chunks with full citation metadata.
- **Delivered:** 2026-04-01
- **Tests:** 14 new (43 total)
- **Note:** USDA Duke ingester ready but no CSV data sourced yet

### Phase 4: RAG Services ✅ COMPLETE (SPR-004)
RAGPipeline.run() returns synthesized answer with inline citations [1][2].
- **Delivered:** 2026-04-01
- **Tests:** 22 new (65 total)
- **Defects:** DEF-002 (ChromaDB version pin — fixed)
- **Note:** SPR-003 and SPR-004 ran in parallel (two Developer Agents)

### Phase 5: API Controllers 🟡 ACTIVE (SPR-005)
POST /api/query, GET /api/herbs, GET /api/status return correct JSON.
- **Assigned to:** Developer Agent A (`herbalism_rag_dev`)
- **Running parallel with:** SPR-006

### Phase 6: Frontend 🟡 ACTIVE (SPR-006)
Dark botanical UI renders, query to answer to source cards works end-to-end.
- **Assigned to:** Developer Agent B (`herbalism_rag_dev_secondary`)
- **Running parallel with:** SPR-005

### Phase 7: Integration and Verification ⬜ NOT STARTED (SPR-007)
10 queries tested, all source URLs resolve, final code pushed to GitHub.

## 5. Key Documents
- **BLU-001:** System Architecture
- **BLU-002:** RAG Pipeline
- **RES-001:** Data Sources Research
- **PRJ-002:** Operational Context & Institutional Knowledge
- **RUN-002:** Multi-Workspace Operations Runbook

## 6. Change Log
| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| 2026-03-31 | 1.0.0 | Initial roadmap | Architect Agent |
| 2026-04-01 | 2.0.0 | Updated with actual status — phases 1-4 complete, 5-6 active. Added PRJ-002 and RUN-002 references. | Architect Agent |
