---
id: BLU-002
title: "Herbalism RAG — RAG Pipeline"
type: explanation
status: APPROVED
owner: architect
agents: [all]
created: 2026-03-31
version: 1.0.0
---

> **BLUF:** Query → local embed → ChromaDB semantic search (top 8 chunks) → Claude Haiku synthesis → structured response with inline citations and source metadata.

# BLU-002: RAG Pipeline

## 1. End-to-End Flow

```
1. User types question in browser
2. POST /api/query {question: "..."}
3. Controller delegates to RAGPipeline.run(question)
4. RetrieverService embeds question (all-MiniLM-L6-v2, local, no API cost)
5. HerbRepository.search(embedding, n=8) -> top 8 HerbChunks from ChromaDB
6. GeneratorService.synthesize(question, chunks) -> Claude Haiku API call
7. Claude returns answer with inline citations [1][2]...
8. QueryResponse built: {answer, sources[], query_time_ms}
9. Frontend renders answer + source cards
```

## 2. Embedding

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Runs:** Locally on CPU — no API call, no cost, no privacy leak
- **Dimension:** 384
- **Usage:** Both at ingest time (chunks) and query time (question)

## 3. Retrieval

- **Store:** ChromaDB persistent collection `herb_chunks`
- **Strategy:** Cosine similarity, top_k = 8
- **Metadata returned with each chunk:**
  - `source_type`: PubMed | MSK | USDA Duke | WHO
  - `title`: Document title
  - `url`: Direct link to source
  - `year`: Publication year
  - `herbs`: List of herb names mentioned
  - `chunk_index`: Position within original document

## 4. Claude Prompt Design

```
System:
You are a herbalism research assistant. Answer questions using ONLY the
provided source excerpts. For every factual claim, cite the source number
in brackets like [1] or [2]. Do not add information not present in the
sources. If the sources do not contain enough information to answer fully,
say so explicitly.

User:
Question: {question}

Sources:
[1] {chunk_1.title} ({chunk_1.source_type}, {chunk_1.year})
{chunk_1.text}

[2] {chunk_2.title} ({chunk_2.source_type}, {chunk_2.year})
{chunk_2.text}
...
```

## 5. Response Schema

```json
{
  "answer": "For cortisol reduction combined with insulin sensitization, the strongest evidence supports ashwagandha [1], berberine [2], and holy basil [3]...",
  "sources": [
    {
      "source_type": "PubMed",
      "title": "Adaptogenic and Anxiolytic Effects of Ashwagandha Root Extract",
      "url": "https://pubmed.ncbi.nlm.nih.gov/23439798/",
      "year": "2012",
      "excerpt": "Ashwagandha significantly reduced serum cortisol levels..."
    }
  ],
  "query_time_ms": 1240
}
```

## 6. Domain Model: HerbChunk

```python
@dataclass
class HerbChunk:
    id: str              # e.g. "pubmed-23439798-chunk-0"
    text: str            # The actual excerpt
    source_type: str     # "PubMed" | "MSK" | "USDA Duke" | "WHO"
    title: str
    url: str
    year: str
    herbs: list[str]     # Herb names mentioned
    chunk_index: int

    def to_source(self) -> Source:
        return Source(
            source_type=self.source_type,
            title=self.title,
            url=self.url,
            year=self.year,
            excerpt=self.text[:300]
        )
```

## 7. Chunking Strategy

- **Chunk size:** 512 tokens
- **Overlap:** 50 tokens
- **Splitter:** Sentence-aware (no mid-sentence splits)
- **Min chunk size:** 100 tokens (discard shorter fragments)

## 8. Performance Expectations

| Step | Expected Time |
|:-----|:-------------|
| Embed question (local) | ~50ms |
| ChromaDB search | ~20ms |
| Claude Haiku API call | ~800-1500ms |
| Total end-to-end | ~1-2s |

The LLM call dominates. Backend language or DB choice has negligible impact on perceived latency.

## 9. Change Log

| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| 2026-03-31 | 1.0.0 | Initial pipeline blueprint | Architect Agent |
