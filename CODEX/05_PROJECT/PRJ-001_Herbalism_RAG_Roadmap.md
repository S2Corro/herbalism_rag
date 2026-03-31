---
id: PRJ-001
title: "Herbalism RAG — Project Roadmap"
type: explanation
status: APPROVED
owner: human
agents: [all]
created: 2026-03-31
version: 1.0.0
---

> **BLUF:** Herbalism RAG answers natural language herbalism questions using evidence from PubMed, MSK, USDA Duke, and WHO — every answer is cited.

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

### Phase 1: Scaffold
FastAPI starts, GET /api/status returns ok, .env wired, gitignore set

### Phase 2: Domain + Repository
HerbRepository add/search round-trip works, ChromaDB persists to disk

### Phase 3: Ingestion Services
scripts/ingest.py populates 500+ chunks with full citation metadata

### Phase 4: RAG Services
RAGPipeline.run() returns synthesized answer with inline citations [1][2]

### Phase 5: API Controllers
POST /api/query, GET /api/herbs, GET /api/status return correct JSON

### Phase 6: Frontend
Dark botanical UI renders, query to answer to source cards works end-to-end

### Phase 7: Integration and Verification
10 queries tested, all source URLs resolve, final code pushed to GitHub

## 5. Key Documents
- BLU-001: System Architecture
- BLU-002: RAG Pipeline
- RES-001: Data Sources Research

## 6. Change Log
| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| 2026-03-31 | 1.0.0 | Initial roadmap | Architect Agent |
