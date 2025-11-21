# VibeForge Research Assistant Refactor — Initial Baseline & Plan

**Date:** November 20, 2025  
**Objective:** Refactor VibeForge Research Assistant to delegate all external search to DataForge via NeuroForge  
**Status:** Initial Assessment & Planning Phase

---

## 1. CURRENT STATE ASSESSMENT

### 1.1 VibeForge Research Assistant (Frontend)

**File:** `/home/charles/projects/Coding2025/Forge/vibeforge/src/lib/components/research/ResearchAssistDrawer.svelte`

**Current Implementation:**

- **Type:** Right-side drawer panel component (modal overlay)
- **Mode:** Demonstration/stub
- **Data:** Entirely hardcoded mock data (snippets, notes, suggestions)
- **Functionality:**
  - Tab system: Notes | Snippets | Suggestions
  - Notes textarea (local state, no persistence)
  - Insert snippet buttons (mock snippets pre-defined)
  - Prompting suggestions (static list)
- **External API Calls:** ❌ NONE (completely local, mock data)
- **Backend Integration:** ❌ NO NeuroForge or DataForge integration

**State Management:**

- Local Svelte runes: `$state()`
- No store integration (isolated component state)
- No async/await or fetch logic

**UX Layout:**

- Right-side modal drawer (max-width: 28rem)
- Dark/light theme support
- Tailwind CSS styling

### 1.2 NeuroForge Backend (Current Routers)

**Existing Routers:**

- `/routers/inference.py` — Status, batch processing, history (no research)
- `/routers/resources.py` — Resource management
- `/routers/analytics.py` — Analytics endpoints
- `/routers/admin.py` — Admin functions

**Current Search Integration:**

- ❌ No `/research/*` endpoints
- ❌ No DataForge search orchestration
- ❌ No external source coordination

**Available Services:**

- Context builder (DataForge → NeuroForge)
- Model router (ensemble voting)
- Evaluator (LLM-based scoring)
- Prompt engine (domain-specific templates)
- Post-processor (output formatting)

### 1.3 DataForge Backend (Current Search)

**File:** `/home/charles/projects/Coding2025/Forge/DataForge/app/api/search_router.py`

**Current Implementation:**

- `POST /api/search` — Semantic search on indexed documents
- `GET /api/search/stats` — Knowledge base statistics
- **Scope:** Internal knowledge base only (no external sources)
- **Architecture:** Uses pgvector for similarity search

**Web Crawler Service:**

- `app/services/webcrawler.py` — Async HTTP crawler with Rust acceleration
- **Features:** Content deduplication, HTML cleaning, embeddings
- **Current Use:** Ingesting documents into knowledge base (not external search)

**Missing:** `/search/external` endpoint for multi-source research

---

## 2. REFACTOR GOALS (5-10 Bullets)

1. **Eliminate Direct External Calls** — VibeForge must never directly call Stack Overflow, Discord, GitHub, or external docs APIs.

2. **Clean API Contract** — Define type-safe, versioned contracts between VibeForge → NeuroForge → DataForge for research queries.

3. **Multi-Source Connector Pattern** — DataForge `/search/external` should support pluggable connectors (StackOverflow, Discord, GitHub, Docs) without rewrites.

4. **LLM-Powered Re-ranking** — NeuroForge receives raw results from DataForge and uses LLM to re-rank, summarize, and cite.

5. **Graceful Degradation** — If DataForge is slow/down, return partial results with clear error messaging (not fail-hard).

6. **Observability & Tracing** — Log query paths, source mix, latency per connector, and final answer quality.

7. **Testability** — Each layer mockable independently (VibeForge → NeuroForge → DataForge stubs).

8. **Config-Driven Behavior** — Timeouts, rate limits, source preferences, LLM model choice all from environment.

9. **UI Consistency** — Research Assistant integrates naturally into VibeForge's 3-column layout (Context | Prompt | Output).

10. **Incremental Rollout** — Phase 1: DataForge connector for one source (StackOverflow). Phase 2: Multi-source + LLM re-ranking.

---

## 3. END-TO-END ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                     VibeForge Frontend (SvelteKit)                   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Output Column                                               │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │ Research Assistant Panel (NEW)                       │  │   │
│  │  │                                                       │  │   │
│  │  │ • Input field: "What do you want to research?"       │  │   │
│  │  │ • Source selector: □ StackOverflow □ Discord …       │  │   │
│  │  │ • [Search Button]                                    │  │   │
│  │  │                                                       │  │   │
│  │  │ Loading state / Final Answer / Error state          │  │   │
│  │  │                                                       │  │   │
│  │  │ Sources section: [clickable links]                  │  │   │
│  │  │ [Raw Evidence tab] (optional debug view)            │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ↓ HTTP POST /research/query                                       │
└──────────────────────────────────────────────────────────────────────┘
                         │
                         │ JSON
                         ↓
┌──────────────────────────────────────────────────────────────────────┐
│             NeuroForge Backend (FastAPI)                             │
│                                                                      │
│  POST /research/query  (NEW ENDPOINT)                               │
│                                                                      │
│  1. Parse request (query, sources, max_results)                    │
│  2. Call DataForge /search/external                                │
│  3. Receive normalized chunks + metadata                           │
│  4. LLM Re-ranking:                                                │
│     - Score relevance                                              │
│     - Prioritize most important snippets                           │
│  5. LLM Synthesis:                                                 │
│     - Short summary                                                │
│     - Long explanation                                             │
│     - Bullet key points                                            │
│     - Cite sources (URL + snippet context)                         │
│  6. Return structured answer                                       │
│                                                                      │
│  ↓ HTTP POST /search/external                                      │
└──────────────────────────────────────────────────────────────────────┘
                         │
                         │ JSON
                         ↓
┌──────────────────────────────────────────────────────────────────────┐
│             DataForge Backend (FastAPI + PostgreSQL)                 │
│                                                                      │
│  POST /search/external  (NEW ENDPOINT)                              │
│                                                                      │
│  1. Parse request (query, sources: ["stackoverflow", "github", …])  │
│  2. Fan out to connectors:                                          │
│     ├─ StackOverflow Connector:                                     │
│     │  └─ Query StackOverflow API / cached index                   │
│     ├─ GitHub Connector:                                            │
│     │  └─ Query GitHub API / cached issues+PRs                     │
│     ├─ Discord Connector:                                           │
│     │  └─ Query community forum archives                           │
│     └─ Docs Connector:                                              │
│        └─ Query indexed documentation (web crawl)                  │
│                                                                      │
│  3. Collect results (title, snippet, URL, source_type, score)      │
│  4. Clean via Rust-accelerated HTML processing                     │
│  5. Deduplicate + rank by relevance                                │
│  6. Return top N results as normalized chunks                      │
│                                                                      │
│  Result: {                                                          │
│    "snippets": [                                                    │
│      {                                                              │
│        "url": "https://...",                                        │
│        "title": "...",                                              │
│        "snippet": "...",                                            │
│        "source": "stackoverflow",                                   │
│        "score": 0.92,                                               │
│        "indexed_at": "2025-11-20T..."                              │
│      },                                                             │
│      ...                                                            │
│    ]                                                                │
│  }                                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. API CONTRACTS (Type Definitions)

### 4.1 NeuroForge: POST /research/query

**Request:**

```json
{
  "query": "How do I implement circuit breaker pattern in Python?",
  "sources": ["stackoverflow", "github", "docs"],
  "max_results": 10,
  "max_tokens_output": 1500,
  "include_evidence": false,
  "timeout_seconds": 30
}
```

**Pydantic Model:**

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class SourceType(str, Enum):
    STACKOVERFLOW = "stackoverflow"
    GITHUB = "github"
    DISCORD = "discord"
    DOCS = "docs"

class ResearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500)
    sources: List[SourceType] = Field(default=[SourceType.STACKOVERFLOW, SourceType.DOCS])
    max_results: int = Field(default=10, ge=1, le=50)
    max_tokens_output: int = Field(default=1500, ge=500, le=4000)
    include_evidence: bool = Field(default=False)
    timeout_seconds: int = Field(default=30, ge=10, le=120)
```

**Response:**

```json
{
  "research_id": "rsch-uuid-12345",
  "query": "How do I implement circuit breaker pattern in Python?",
  "status": "completed",
  "summary": "A circuit breaker is a design pattern that prevents cascading failures...",
  "explanation": "The circuit breaker pattern works by monitoring for failures...",
  "key_points": [
    "Maintains state: CLOSED (normal) → OPEN (fail-fast) → HALF_OPEN (recovery)",
    "Prevents repeated calls to failing services",
    "Implements exponential backoff for retries"
  ],
  "sources": [
    {
      "url": "https://stackoverflow.com/questions/...",
      "title": "Circuit Breaker Pattern in Python",
      "source": "stackoverflow",
      "relevance_score": 0.95,
      "citation_index": 1
    },
    {
      "url": "https://github.com/.../circuit-breaker-python",
      "title": "Python Circuit Breaker Library",
      "source": "github",
      "relevance_score": 0.87,
      "citation_index": 2
    }
  ],
  "evidence": [
    {
      "snippet": "A circuit breaker is a design pattern used in software development...",
      "source_id": 1,
      "confidence": 0.92
    }
  ],
  "latency_ms": {
    "dataforge_search": 450,
    "llm_processing": 680,
    "total": 1130
  },
  "error": null
}
```

**Pydantic Response Model:**

```python
class Citation(BaseModel):
    url: str
    title: str
    source: SourceType
    relevance_score: float = Field(ge=0.0, le=1.0)
    citation_index: int

class EvidenceSnippet(BaseModel):
    snippet: str
    source_id: int
    confidence: float

class LatencyMetrics(BaseModel):
    dataforge_search: int
    llm_processing: int
    total: int

class ResearchQueryResponse(BaseModel):
    research_id: str
    query: str
    status: str
    summary: str
    explanation: str
    key_points: List[str]
    sources: List[Citation]
    evidence: List[EvidenceSnippet] = Field(default=[])
    latency_ms: LatencyMetrics
    error: Optional[str] = None
```

---

### 4.2 DataForge: POST /search/external

**Request:**

```json
{
  "query": "circuit breaker pattern",
  "sources": ["stackoverflow", "github"],
  "max_results_per_source": 3,
  "filters": {
    "language": "python",
    "date_range_days": 365
  }
}
```

**Pydantic Model:**

```python
class ExternalSearchFilters(BaseModel):
    language: Optional[str] = None
    date_range_days: Optional[int] = 365
    tags: Optional[List[str]] = None

class ExternalSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    sources: List[SourceType]
    max_results_per_source: int = Field(default=3, ge=1, le=10)
    filters: Optional[ExternalSearchFilters] = None
    timeout_seconds: int = Field(default=20, ge=5, le=60)
```

**Response:**

```json
{
  "search_id": "srch-uuid-67890",
  "query": "circuit breaker pattern",
  "sources_queried": ["stackoverflow", "github"],
  "total_results": 5,
  "snippets": [
    {
      "id": "so-12345",
      "url": "https://stackoverflow.com/questions/...",
      "title": "Circuit Breaker Pattern in Python",
      "source": "stackoverflow",
      "snippet": "A circuit breaker is a design pattern that prevents cascading failures...",
      "score": 0.95,
      "indexed_at": "2025-11-20T10:30:00Z",
      "tags": ["python", "design-pattern", "resilience"]
    },
    {
      "id": "gh-67890",
      "url": "https://github.com/...",
      "title": "python-circuit-breaker",
      "source": "github",
      "snippet": "A simple circuit breaker implementation for Python with async support...",
      "score": 0.87,
      "indexed_at": "2025-11-20T08:15:00Z",
      "tags": ["python", "library", "circuit-breaker"]
    }
  ],
  "errors": {
    "discord": "Failed to query: timeout after 5s"
  }
}
```

**Pydantic Response Model:**

```python
class ExternalSearchSnippet(BaseModel):
    id: str
    url: str
    title: str
    source: SourceType
    snippet: str
    score: float = Field(ge=0.0, le=1.0)
    indexed_at: str  # ISO 8601
    tags: List[str] = Field(default=[])

class ExternalSearchResponse(BaseModel):
    search_id: str
    query: str
    sources_queried: List[SourceType]
    total_results: int
    snippets: List[ExternalSearchSnippet]
    errors: Dict[str, str] = Field(default={})
```

---

## 5. IMPLEMENTATION LAYERS & MODULES

### Layer 1: DataForge Backend (`app/api/search_external_router.py`)

**New Endpoint:** `POST /api/search/external`

**Modules to Create:**

- `app/connectors/base_connector.py` — Abstract connector interface
- `app/connectors/stackoverflow_connector.py` — StackOverflow search
- `app/connectors/github_connector.py` — GitHub search
- `app/connectors/discord_connector.py` — Discord archive search
- `app/connectors/docs_connector.py` — Web crawler for indexed docs
- `app/services/external_search_service.py` — Orchestrator (fan-out, dedup, rank)

### Layer 2: NeuroForge Backend (`routers/research.py`)

**New Endpoint:** `POST /research/query`

**Modules to Create:**

- `services/research_orchestrator.py` — Calls DataForge, invokes LLM
- `services/research_summarizer.py` — LLM-based re-ranking and synthesis
- `adapters/research_domain_adapter.py` — Research-specific prompt templates

### Layer 3: VibeForge Frontend

**Components to Create/Refactor:**

- `src/lib/components/research/ResearchPanel.svelte` — Main UI panel
- `src/lib/stores/researchStore.ts` — State management for queries, results
- `src/lib/api/research.ts` — API client for `/research/query`

---

## 6. PHASED ROLLOUT

### Phase 1: Foundation (Week 1)

1. Design & validate API contracts
2. Create DataForge connector base class + StackOverflow connector
3. Implement DataForge `/search/external` endpoint
4. Add NeuroForge `/research/query` stub (minimal LLM)

### Phase 2: LLM Integration (Week 2)

5. Implement NeuroForge research summarizer (real LLM re-ranking)
6. Add evidence extraction and citation generation
7. Implement graceful degradation (partial results on failure)

### Phase 3: Frontend Integration (Week 3)

8. Refactor VibeForge Research Assistant UI
9. Wire to `/research/query` endpoint
10. Add loading, error, and result rendering states

### Phase 4: Additional Sources (Week 4)

11. Add GitHub, Discord, Docs connectors
12. Comprehensive testing and observability
13. Deploy to production

---

## 7. SUCCESS CRITERIA

✅ **Functional:**

- VibeForge never calls external APIs directly
- Multi-source research returns deduplicated results
- LLM re-ranks and synthesizes answers with citations
- Graceful degradation on connector failures

✅ **Non-Functional:**

- <2s latency for small queries (<10 results)
- <5% error rate on research queries
- 95%+ cache hit rate on repeated queries
- Observability: log every research query with sources, latency, LLM cost

✅ **Code Quality:**

- Each connector independently testable
- API contracts versioned and documented
- Type safety throughout (Pydantic + TypeScript)
- 80%+ test coverage for research services

---

## Next Step

Ready to proceed! Share:

1. **VibeForge Output Column context** — Where should Research Panel live?
2. **NeuroForge config.py** — Where to add research timeouts/limits?
3. **DataForge credentials** — StackOverflow API key location?

Then we'll **start with Phase 1: API contracts + DataForge connector base**.
