---
id: BLU-001
title: "Herbalism RAG — System Architecture"
type: explanation
status: APPROVED
owner: architect
agents: [all]
created: 2026-03-31
version: 1.1.0
---

> **BLUF:** Modular monolith using Python/FastAPI with strict Controller/Service/Repository layering. One process, four clean modules. Dependencies flow downward only.

# BLU-001: System Architecture

## 1. Pattern: Modular Monolith

One process, one deployment, clean module boundaries. Chosen over:
- Plain monolith: no enforced separation, becomes unmaintainable
- Microservices: overkill at this scale; bottleneck is always the LLM call (~1-3s), not the backend language

The module boundaries are identical to what microservice split-points would be — so extraction is possible later without restructuring.

## 2. Layering: Controller / Service / Repository

Dependencies flow DOWNWARD only. No layer may call upward.

```
HTTP Request
     |
CONTROLLER (api/)       — speaks HTTP only, no business logic
     |
SERVICE (rag/, ingest/) — all business logic, no HTTP, no DB SDK calls
     |
REPOSITORY (db/)        — only code that touches ChromaDB SDK
     |
ChromaDB + sentence-transformers
```

## 3. Tech Stack Decisions

| Component | Choice | Reason |
|:----------|:-------|:-------|
| Language | Python 3.11+ | Best AI/ML ecosystem; all SDKs Python-native |
| Framework | FastAPI | Async, Pydantic-native, auto OpenAPI docs |
| LLM | Anthropic Claude Haiku | Fast, cheap, great at citation synthesis |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Local, free, CPU-runnable, no privacy leak |
| Vector DB | ChromaDB (embedded) | No separate server, persistent, swap-friendly |
| Frontend | Vanilla HTML/CSS/JS | Served as static files by FastAPI |
| Key security | .env + .gitignore | User-managed, never committed, server-side only |

## 4. Full Directory Structure

```
herbalism_rag/
|
|- backend/
|   |- __init__.py                # Package marker
|   |- main.py                    # FastAPI app factory, mounts routes + static
|   |- config.py                  # Pydantic Settings, reads from .env
|   |
|   |- api/                       # CONTROLLER LAYER
|   |   |- __init__.py
|   |   |- routes/
|   |   |   |- __init__.py
|   |   |   |- query.py           # POST /api/query
|   |   |   |- herbs.py           # GET /api/herbs
|   |   |   |- status.py          # GET /api/status
|   |   |- schemas/
|   |       |- __init__.py
|   |       |- requests.py        # QueryRequest
|   |       |- responses.py       # QueryResponse, Source, StatusResponse
|   |
|   |- rag/                       # SERVICE LAYER — RAG domain
|   |   |- __init__.py
|   |   |- pipeline.py            # RAGPipeline.run(question) -> QueryResponse
|   |   |- retriever.py           # RetrieverService.search(question) -> [HerbChunk]
|   |   |- generator.py           # GeneratorService.synthesize(q, chunks) -> str
|   |
|   |- ingest/                    # SERVICE LAYER — Ingestion domain
|   |   |- __init__.py
|   |   |- pubmed.py              # PubMedIngestor.run(herb_list)
|   |   |- msk_herbs.py           # MSKIngestor.run()
|   |   |- usda_duke.py           # DukeIngestor.run(csv_path)
|   |
|   |- db/                        # REPOSITORY LAYER
|   |   |- __init__.py
|   |   |- herb_repository.py     # HerbRepository: add(), search(), list(), stats()
|   |
|   |- models/                    # DOMAIN MODELS — shared, no layer owns them
|       |- __init__.py
|       |- herb_chunk.py          # HerbChunk dataclass
|
|- frontend/
|   |- index.html
|   |- css/style.css              # Dark botanical design system
|   |- js/app.js                  # Query logic, response rendering, source cards
|
|- data/
|   |- chroma_db/                 # Persistent vector store (gitignored)
|   |- usda_duke/                 # Duke CSV files (gitignored)
|   |- seeds/
|       |- who_monographs.json    # Curated WHO data (committed)
|
|- scripts/
|   |- ingest.py                  # Runs all ingesters in sequence
|
|- tests/                         # Test suite
|   |- test_*.py                  # Naming: test_{module}.py
|
|- .env.example
|- .gitignore
|- requirements.txt
|- pyproject.toml                 # Project/tooling config (pytest, mypy, ruff)
|- README.md
```

## 5. Layer Contracts

### Controller — thin, HTTP only
```python
@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    return await rag_pipeline.run(request.question)
```

### Service — all business logic
```python
class RAGPipeline:
    async def run(self, question: str) -> QueryResponse:
        chunks = await self.retriever.search(question)
        answer = await self.generator.synthesize(question, chunks)
        return QueryResponse(answer=answer, sources=[c.to_source() for c in chunks])
```

### Repository — only ChromaDB contact point
```python
class HerbRepository:
    def search(self, embedding: list[float], n: int = 8) -> list[HerbChunk]:
        results = self.collection.query(query_embeddings=[embedding], n_results=n)
        return [HerbChunk.from_chroma(r) for r in results]
```

## 6. API Endpoints

| Method | Path | Description |
|:-------|:-----|:------------|
| POST | /api/query | Main RAG query — returns answer + sources |
| GET | /api/herbs | List indexed herb names |
| GET | /api/status | Health + ChromaDB chunk count |

## 7. Change Log

| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| 2026-03-31 | 1.1.0 | Apply EVO-001: add `__init__.py`, `tests/`, `pyproject.toml` to dir tree | Architect Agent |
| 2026-03-31 | 1.0.0 | Initial architecture | Architect Agent |
