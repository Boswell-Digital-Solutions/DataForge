# §2 — Architecture

## Component Map

```
DataForge (port 8001)
│
├── FastAPI Application Layer
│   ├── 29 API routers
│   ├── Lifespan handler (CORS, startup/shutdown)
│   ├── Static file serving
│   └── Admin UI (Jinja2 template)
│
├── Business Logic Layer
│   ├── CRUD operations (app/api/crud.py)
│   ├── Hybrid search engine (app/api/search.py)
│   ├── Embedding pipeline (app/utils/embeddings.py)
│   ├── Auth utilities (app/utils/auth.py)
│   └── Anomaly detection (inline with auth)
│
├── ORM Layer
│   ├── SQLAlchemy models (app/models/models.py) — 31+ classes
│   ├── Pydantic schemas (app/models/schemas.py) — 90+ schemas
│   └── Session dependency (app/database.py)
│
└── Storage Layer
    ├── PostgreSQL 13+ — primary relational store
    ├── pgvector extension — ANN index (IVFFlat, cosine)
    └── Redis 6+ — cache, rate limiting, session data
```

## Hybrid Search Architecture

DataForge's search system is the core knowledge retrieval engine. It combines two complementary scoring functions and merges results via Reciprocal Rank Fusion.

### Pipeline

```
Query Text
    │
    ├──► Embedding Model (Voyage AI) ──► 1536-dim vector
    │                                        │
    │                                   pgvector ANN
    │                                   (cosine sim)
    │                                        │
    └──► PostgreSQL TSVECTOR ──► BM25 ranking
                                        │
                    Both result sets ──► Reciprocal Rank Fusion (RRF)
                                        │
                                   Merged + scored results
                                        │
                               Filter by similarity threshold
                               (DEFAULT: 0.7)
```

### RRF Formula

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

Where `k = 60` (standard constant) and `rank_i(d)` is document `d`'s rank in result set `i`. This formula neutralizes outlier ranks and rewards consistent top placement across both retrieval methods.

**Measured improvement:** +40% retrieval accuracy versus pure semantic search.

### Search Configuration

| Parameter | Default | Max |
|-----------|---------|-----|
| `DEFAULT_SEARCH_LIMIT` | 5 | — |
| `MAX_SEARCH_LIMIT` | 100 | — |
| `DEFAULT_SIMILARITY_THRESHOLD` | 0.7 | 1.0 |
| `MAX_EMBEDDING_INPUT_LENGTH` | 8000 chars | — |
| Chunk size | 500 tokens | — |
| Chunk overlap | 50 tokens | — |

### Embedding Providers

| Provider | Dimensions | Role |
|----------|-----------|------|
| Voyage AI (`voyage-large-2`) | 1536 | Default |
| Voyage AI (`voyage-2`) | 1024 | Alternate |
| OpenAI | 1536 | Fallback |
| Cohere | varies | Fallback |

### Vector Index

- **Type:** IVFFlat (Inverted File with Flat quantization)
- **Distance metric:** Cosine
- **Extension:** pgvector 0.2.4
- **Index behavior:** Approximate nearest neighbor; trades small accuracy loss for large speed gains at scale

## Document-to-Chunk Pipeline

Triggered automatically on document create or update:

```
Document (full text)
    │
    ▼
Text Splitter
(500 tokens, 50 overlap)
    │
    ▼
Chunk records (Chunk ORM model)
    │
    ▼
Embedding model invocation
(Voyage AI, batch)
    │
    ▼
pgvector column update
(1536-dim float array)
    │
    ▼
TSVECTOR column update
(PostgreSQL full-text index)
```

Chunking runs synchronously for small documents and can be deferred via Celery for large batches.

## Multi-Tenant Architecture

DataForge supports multiple domains, each with isolated knowledge spaces:

```
Domain A (e.g., NeuroForge)
├── Documents (tagged, domain-scoped)
├── Chunks (embedded, domain-indexed)
└── Search (domain-filtered by default)

Domain B (e.g., AuthorForge)
├── Documents
├── Chunks
└── Search
```

**Isolation mechanism:** Domain foreign keys on Document and Chunk models. Search queries accept `domain_id` filter. Without explicit domain filtering, cross-domain search is possible (authorized use cases only).

## Execution Index Architecture

The `ExecutionIndex` model provides a denormalized fast-path for run queries:

```
ForgeCommand creates run record
    │
    ▼
ExecutionIndex row (run_id PK, status, outcome, mode, timing)
    │     ← Fast reads, no joins needed
    ▼
RunEvidence row (full JSONB blob)
    │     ← Deep inspection when needed
    ▼
BugCheckRunModel / NeuroForgeRun / etc.
      ← Domain-specific structured records
```

This two-layer pattern keeps status queries sub-millisecond while preserving full evidence fidelity.

## Cache Architecture (Redis)

Redis serves three purposes:

1. **Response cache** — frequently read documents and search results
2. **Rate limiting** — distributed token bucket, per-user and global
3. **Session data** — OAuth state parameters, TOTP challenges

```
Redis Sentinel
├── Primary node (writes)
└── Replica nodes (reads)
    └── Automated failover < 10 seconds
```

The `/cache` and `/cache-replication` routers manage cache sync and failover signaling.

## Resilience Architecture

| Layer | Strategy | Recovery Time |
|-------|----------|--------------|
| PostgreSQL | Primary-replica + automated failover | < 30s |
| Redis | Sentinel-managed failover | < 10s |
| API | Load balancer + health checks + graceful shutdown | < 5s |
| Downstream calls | Circuit breaker (fail-fast) | Configurable |
| Async tasks | Celery + DLQ, exponential backoff | 3 retries, 60s max |
| Rate limiting | Distributed Redis token bucket | Per-user + global |

## Admin UI

A self-contained HTML interface (`templates/admin.html`) is served at `/admin-ui`. It provides:
- Document browse and create
- Domain and tag management
- Search testing interface
- Rendered server-side via Jinja2

No JavaScript framework dependency; the admin UI is a single-file template.
