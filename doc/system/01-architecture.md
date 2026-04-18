# §2 — Architecture

## Component Map

```
DataForge (default port 8001)
│
├── FastAPI Application Layer
│   ├── 35 mounted router objects plus app-level health/admin/docs routes
│   ├── Lifespan handler (config validation, pgvector startup checks, readiness posture)
│   ├── Correlation, timeout, and security-header middleware
│   ├── HTML admin/diligence views plus JSON API surfaces
│   └── Static file serving when `static/` is present
│
├── Mounted Service Domains
│   ├── Search and content admin
│   ├── Auth compatibility, admin key control, token rotation
│   ├── AuthorForge, VibeForge, NeuroForge, Forge:SMITH, Teams
│   ├── ForgeAgents, BugCheck, experience store, run persistence
│   ├── Diligence UI/API, Tarcie ingest, events/audit surfaces
│   ├── Runtime promotion, policy envelopes, rate-limit governance
│   ├── Multi-provider catalog/pricing/costs/batch
│   ├── Sentinel, compression, press automation, private-source profiles
│   └── FPVS health, readiness, and version probes
│
├── Model and Schema Layer
│   ├── Core shared tables in `app/models/models.py`
│   ├── Core shared schemas in `app/models/schemas.py`
│   ├── Domain-specific `*_models.py` and `*_schemas.py` modules
│   └── Session dependency and engine wiring in `app/database.py`
│
├── Utility and Integration Layer
│   ├── Hybrid search engine (`app/api/search.py`)
│   ├── Embedding pipeline (`app/utils/embeddings.py`)
│   ├── Cache governance + corpus versioning
│   ├── Auth, encryption, tracing, resilience, and failover helpers
│   └── Nested `forge-telemetry/` library boundary for shared telemetry concerns
│
└── Storage Layer
    ├── PostgreSQL 13+ — canonical relational store and authority boundary
    ├── pgvector extension — ANN index (IVFFlat, cosine)
    └── Redis / Redis Cloud — derived cache only (disposable, TTL-bound)
```

## Mounted Versus Source-Present Surface

`app/api/` currently contains more router modules than the live app mounts. The live contract
is whatever `app.main:app` includes. Source-present but unmounted routers such as
`auth_secure_router`, `tracing_router`, `api_deployment_router`, `replication_router`,
`cache_replication_router`, `dlq_router`, and `rate_limit_router` remain implementation
inventory only until explicitly registered in `app/main.py`.

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

Redis is treated as derived state, never as authority. The governing rule is:

```
Postgres/Supabase = source of truth
Redis = disposable acceleration layer
```

Current Redis responsibilities:

1. **Document cache** — `doc:{id}` with explicit TTL
2. **Retrieval cache** — version-aware result keys that include corpus version
3. **Embedding cache** — hash-addressed embedding results with explicit TTL
4. **Short-lived auth-adjacent state** — OAuth/TOTP/session helper records
5. **Rate limiting and token revocation** — fast-path enforcement, but never allow-on-miss
6. **Corpus current-version cache** — `corpus_version:current` with a 60-second TTL

### Deterministic Retrieval Keys

Retrieval keys include all inputs required to avoid stale or cross-scope reuse:

```
retrieval:v{corpus_version}:{embed_model}:{rrf_hash}:{top_k}:{scope}:{query_hash}
```

Where:
- `query_hash` is derived from a canonicalized query string
- `rrf_hash` is derived from sorted JSON config
- `scope` is `domain_id` or `global`
- `corpus_version` is mandatory

### TTL Governance

No Redis write is allowed without TTL. The shared wrapper in
`app/utils/cache_governance.py` rejects writes where `ttl_seconds <= 0`.

### Authority Boundary

Cache lookups may accelerate reads, but authority-adjacent decisions always fall back
to the canonical database path. Redis errors are logged as degraded operation, then the
request re-checks the authoritative source.

## Corpus Versioning

Corpus freshness is tracked with two tables:

1. `corpus_state` — single-row current version (`id = 1`)
2. `corpus_versions` — append-only audit trail of bumps

Every successful document/chunk insert, delete, or reindex bumps the corpus version
atomically with:

```sql
UPDATE corpus_state
SET current_version = current_version + 1,
    updated_at = now()
WHERE id = 1
RETURNING current_version;
```

The returned version is then inserted into `corpus_versions`, and
`corpus_version:current` is invalidated in Redis. Retrieval caches naturally age out
because the version is part of the key.

## Resilience Architecture

| Layer | Strategy | Recovery Time |
|-------|----------|--------------|
| PostgreSQL | Primary-replica + automated failover | < 30s |
| Redis | Cache degradation only; authority checks fall back to DB and rate limiting denies on outage | < 10s |
| API | Load balancer + health checks + graceful shutdown | < 5s |
| Downstream calls | Circuit breaker (fail-fast) | Configurable |
| Async tasks | Celery + DLQ, exponential backoff | 3 retries, 60s max |
| Rate limiting | Redis-backed sliding window with fail-closed deny on Redis outage | Per-user + global |

## Admin UI

A server-rendered HTML interface is served at `/admin` and `/admin-ui`. It provides:
- Document browse and create
- Domain and tag management
- Search testing interface
- Rendered server-side via Jinja2 with companion assets under `static/`

No frontend SPA is mounted inside DataForge. The operator-facing UI surface here remains
server-rendered HTML plus JSON APIs.

---
