# DataForge — Complete System Reference

**Document version:** 1.0 (2026-02-24)

> BDS Documentation Protocol v1.0 — unified reference for AI-assisted development

This document is the **service-level compilation** of all DataForge system documentation. It combines all 11 modular reference sections from `doc/system/` into a single context bundle. For the ecosystem-wide view, see `../doc/SYSTEM.md`.

| Part | Contents |
|------|----------|
| §1 | Service purpose, source-of-truth philosophy, ecosystem role |
| §2 | Component map, hybrid search, vector pipeline, multi-tenant model |
| §3 | Exact dependencies and versions |
| §4 | Directory tree, key files, ORM models |
| §5 | All environment variables with types and defaults |
| §6 | All 33 routers, 100+ endpoints, auth requirements |
| §7 | Vector search, chunking, encryption, anomaly detection |
| §8 | Integration contracts per service (BugCheck, NeuroForge, etc.) |
| §9 | Lifecycle state machine, access control matrix, 409 rules |
| §10 | Test suite structure, coverage, compliance tests |
| §11 | Critical constraints, access control matrix, migration runbook |

---


# §1 — Overview & Philosophy

## Service Identity

**DataForge** is the unified data and knowledge engine of the Forge Ecosystem. It runs on port **8001** and serves as the single, authoritative source of truth for all durable state across every Forge service.

- **Version:** v5.2
- **Status:** 18/18 phases complete
- **Scale:** 42,732 LOC across 133 Python files
- **Tests:** 296/296 passing, 82% coverage
- **Port:** 8001

## The Source-of-Truth Contract

DataForge is not a cache. It is not a secondary store. It is not a convenience API. It is the truth.

Every service in the Forge Ecosystem that produces durable state writes to DataForge. This is a non-negotiable architectural invariant:

- **NeuroForge** writes all LLM run results, model performance metrics, and inference records.
- **VibeForge** writes project sessions, stack outcomes, and code analysis results.
- **AuthorForge** writes all narrative content: books, chapters, scenes, characters, arcs, locations, manuscripts.
- **ForgeAgents / BugCheck** writes findings, lifecycle events, enrichment artifacts, and progress events.
- **Forge:SMITH** writes planning sessions, portfolio projects, evaluation snapshots, and governance events.
- **ForgeCommand** writes run records, lifecycle transitions, and finalization states.

No service maintains a local truth cache. No service treats its own database as canonical. All reads for authoritative state flow through DataForge. All writes that create or mutate durable state flow through DataForge.

**If DataForge is unavailable, runs do not start. This is by design.**

## Ecosystem Role

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Forge Ecosystem                                 │
│                                                                       │
│   NeuroForge  VibeForge  AuthorForge  ForgeAgents  SMITH  BugCheck   │
│       │           │           │            │          │        │      │
│       └───────────┴───────────┴────────────┴──────────┴────────┘      │
│                                   │                                   │
│                            ┌──────▼──────┐                           │
│                            │  DataForge  │  ← The Source of Truth    │
│                            │   (8001)    │                           │
│                            └──────┬──────┘                           │
│                                   │                                   │
│                    ┌──────────────┼──────────────┐                   │
│                    │              │              │                   │
│             ┌──────▼─────┐  ┌────▼────┐  ┌─────▼────┐             │
│             │ PostgreSQL  │  │  Redis  │  │ pgvector  │             │
│             │  (primary)  │  │ (cache) │  │  (ANN)    │             │
│             └─────────────┘  └─────────┘  └──────────┘             │
└───────────────────────────────────────────────────────────────────────┘
```

## Core Responsibilities

### 1. Durable State Persistence
All service state — run records, findings, projects, content, events — is stored in PostgreSQL via SQLAlchemy ORM models. State is never ephemeral unless explicitly designed to be (e.g., Redis cache).

### 2. Semantic Knowledge Retrieval
DataForge stores documents with 1536-dimensional vector embeddings. It provides hybrid search combining cosine similarity (Voyage AI embeddings) with BM25 keyword scoring via Reciprocal Rank Fusion (RRF), delivering +40% accuracy over pure semantic search.

### 3. Authentication & Authorization
DataForge manages the full auth stack: JWT issuance, OAuth2/OIDC flows, TOTP 2FA, API key management, and scoped run tokens. Every write operation to DataForge requires a valid credential.

### 4. Audit & Compliance
An append-only, HMAC-SHA256-signed audit log captures all significant events. Field-level AES-256 Fernet encryption protects PII. Anomaly detection covers six threat patterns. Compliance targets include GDPR, CCPA, HIPAA, SOC2, and PCI-DSS.

### 5. Lifecycle Enforcement
DataForge enforces the BugCheck finding lifecycle state machine at the API level. Invalid transitions return 409 Conflict. After a run is finalized, new findings are rejected with 409. These are invariants, not policies.

### 6. Observability Infrastructure
Prometheus metrics at `/metrics`, OpenTelemetry distributed tracing, structured JSON logging, and a dead-letter queue for failed async tasks.

## What DataForge Is Not

- **Not a message bus.** It does not replace Celery/Redis for async task queuing, though it operates a DLQ.
- **Not a CDN.** Static assets live elsewhere; DataForge serves document content, not binary blobs.
- **Not an orchestrator.** ForgeCommand orchestrates runs; DataForge persists their state.
- **Not an LLM gateway.** NeuroForge routes LLM inference; DataForge stores the results.

## Performance Targets

| Metric | Target |
|--------|--------|
| API latency (p95) | < 100ms |
| Throughput | 1,000+ RPS |
| Uptime SLA | 99.99% |
| PostgreSQL failover | < 30 seconds |
| Redis failover | < 10 seconds |

*See §11 for critical constraints and invariants that must never be violated.*

---


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

---


# §3 — Technology Stack

## Runtime Environment

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Type hints mandatory, async/await throughout |
| FastAPI | 0.109.0 | ASGI framework; lifespan for startup/shutdown |
| uvicorn | 0.27.0 | ASGI server; production behind nginx/load balancer |

## Databases

| Component | Version | Notes |
|-----------|---------|-------|
| PostgreSQL | 13+ | Primary relational store; JSONB, TSVECTOR, arrays |
| pgvector | 0.2.4 | Vector similarity extension; IVFFlat ANN index |
| Redis | 6+ | Cache, rate limiting, session data |

## ORM & Migrations

| Component | Version | Notes |
|-----------|---------|-------|
| SQLAlchemy | 2.0.36 | Core ORM; 2.x async session style |
| psycopg2-binary | 2.9.10 | PostgreSQL driver |
| Alembic | 1.13.1 | Schema migrations; 11 version files |

## Data Validation

| Component | Version | Notes |
|-----------|---------|-------|
| Pydantic | >= 2.10.0 | v2 API; all schemas use model_validator, field_validator |
| Jinja2 | (latest) | Admin UI template rendering only |

## Authentication & Cryptography

| Component | Version | Notes |
|-----------|---------|-------|
| python-jose | 3.3.0 | JWT creation and validation (HS256) |
| passlib | 1.7.4 | Password hashing abstraction |
| bcrypt | 4.1.2 | Bcrypt backend for passlib |
| cryptography | (latest) | AES-256 Fernet for field-level encryption |

## AI / Embedding Providers

| Component | Version | Role |
|-----------|---------|------|
| Voyage AI | 0.2.3 | Primary embedding provider (`voyage-large-2`, 1536-dim) |
| OpenAI | 1.10.0 | Fallback embedding provider |
| Cohere | (latest) | Secondary fallback embedding provider |

## Testing

| Component | Version | Notes |
|-----------|---------|-------|
| pytest | 7.4.3 | Test runner |
| pytest-asyncio | (latest) | Async test support |
| pytest-cov | (latest) | Coverage reporting |
| pytest-mock | (latest) | Mocking utilities |
| httpx | 0.26.0 | Async HTTP client for integration tests |

## HTTP & Networking

| Component | Version | Notes |
|-----------|---------|-------|
| httpx | 0.26.0 | Async HTTP client (tests + internal calls) |
| uvicorn | 0.27.0 | ASGI server |

## Observability

| Component | Notes |
|-----------|-------|
| Prometheus client | Metrics at `/metrics` |
| OpenTelemetry | Distributed tracing with correlation IDs |
| structlog / logging | Structured JSON logging |

## Optional / Load Testing

| Component | Notes |
|-----------|-------|
| k6 | Load testing (optional, not in requirements.txt) |
| Celery | Async task queue (DLQ integration) |

## Deployment Tools

| Component | Notes |
|-----------|-------|
| Docker | Container runtime |
| Docker Compose | Local dev orchestration |
| Kubernetes | Production target (StatefulSets for PG replication) |

## Dependency File

All pinned versions are in `requirements.txt` at the repository root. The `venv/` directory holds the local virtual environment and is not committed to version control.

Key install command:
```bash
pip install -r requirements.txt
```

Never install packages directly into the venv without updating `requirements.txt`. All version pins in this document must remain synchronized with `requirements.txt`.

---


# §4 — Project Structure

## Directory Tree

```
DataForge/
├── alembic/                          # Database migration history
│   ├── env.py                        # Alembic environment config (imports ORM models)
│   ├── script.py.mako                # Migration template
│   └── versions/                     # 13 migration version files
│       ├── 0001_initial_schema.py
│       ├── ...
│       ├── 0012_multi_provider_tables.py
│       └── 0013_sentinel_tables.py
│
├── app/                              # Main application package
│   ├── main.py                       # FastAPI app + lifespan + router registration
│   ├── database.py                   # SQLAlchemy engine, SessionLocal, get_db()
│   │
│   ├── models/
│   │   ├── models.py                 # SQLAlchemy ORM models (31+ classes)
│   │   ├── schemas.py                # Pydantic request/response schemas (90+)
│   │   ├── multi_provider_models.py  # Multi-provider pipeline models (6 tables)
│   │   ├── multi_provider_schemas.py # Multi-provider Pydantic schemas
│   │   ├── sentinel_models.py        # Sentinel health sweep + healing models
│   │   └── sentinel_schemas.py       # Sentinel Pydantic schemas
│   │
│   ├── api/
│   │   ├── search_router.py          # POST /api/search, GET /api/search/stats
│   │   ├── admin_router.py           # Admin CRUD: documents, domains, tags
│   │   ├── auth_router.py            # JWT, OAuth2, TOTP 2FA endpoints
│   │   ├── crud.py                   # Database operations (no business logic)
│   │   ├── search.py                 # Hybrid vector + BM25 search logic
│   │   ├── model_catalog_router.py   # Multi-provider model catalog CRUD
│   │   ├── pricing_router.py         # Pricing snapshots, alerts, monitor runs
│   │   ├── cost_ledger_router.py     # Cost ledger entries + aggregations
│   │   └── sentinel_router.py        # Sentinel sweeps + healing events CRUD
│   │
│   └── utils/
│       ├── embeddings.py             # Text chunking + Voyage AI embedding generation
│       └── auth.py                   # JWT creation/validation + bcrypt helpers
│
├── scripts/
│   ├── create_admin.py               # Interactive CLI: create initial admin user
│   └── seed_model_catalog.py         # Seed 14-model multi-provider catalog
│
├── templates/
│   └── admin.html                    # Self-contained Jinja2 admin UI template
│
├── static/                           # Static assets (CSS, JS) for admin UI
│
├── tests/                            # 32 test files, 296 tests, 82% coverage
│   ├── test_auth.py
│   ├── test_encryption.py
│   ├── test_rate_limiting.py
│   ├── test_anomaly_detection.py
│   ├── test_search.py
│   ├── test_bugcheck_api.py
│   ├── test_neuroforge_api.py
│   ├── test_vibeforge_api.py
│   ├── test_authorforge_api.py
│   ├── test_lifecycle.py
│   ├── test_compliance_gdpr.py
│   └── ... (32 files total)
│
├── alembic.ini                       # Alembic configuration
├── docker-compose.yml                # Local dev: PostgreSQL + Redis + DataForge
├── docker-compose.prod.yml           # Production compose override
├── Dockerfile                        # Multi-stage Python image
├── .env.example                      # All required environment variables documented
├── requirements.txt                  # Pinned Python dependencies
├── pytest.ini                        # pytest configuration + coverage settings
├── mypy.ini                          # Type checking configuration
└── Makefile                          # Common dev tasks (test, lint, migrate, etc.)
```

## Key Files

### `app/main.py`
The FastAPI application entry point. Defines the `lifespan` context manager (startup database checks, shutdown cleanup). Registers all 33 routers with their prefixes. Configures CORS middleware with `ALLOWED_ORIGINS`. Mounts `static/` directory. Registers exception handlers.

**Critical:** The order of router registration matters. Auth routes must be registered before protected routes. The health endpoint (`/health`) must be registered without auth middleware.

### `app/database.py`
Creates the SQLAlchemy `engine` from `DATABASE_URL`. Provides `SessionLocal` for synchronous sessions and `get_db()` as a FastAPI dependency. Also initializes the pgvector extension on first connection.

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `app/models/models.py`
Contains all 31+ SQLAlchemy ORM model classes. Key models:

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | Auth identity (username, email, hashed_password, is_admin) |
| `Domain` | `domains` | Knowledge organization hierarchy |
| `Document` | `documents` | Content storage + publication state + metadata JSONB |
| `Chunk` | `chunks` | Text segments + pgvector embedding + TSVECTOR |
| `Tag` | `tags` | Labels; many-to-many via `document_tags` |
| `ExecutionIndex` | `execution_index` | Fast run status lookups (run_id PK, denormalized) |
| `RunEvidence` | `run_evidence` | Full JSONB evidence blobs |
| `AgentRegistry` | `agent_registry` | Agent configuration persistence |
| `BugCheckRunModel` | `bugcheck_runs` | BugCheck run records |
| `BugCheckFindingModel` | `bugcheck_findings` | Individual findings with lifecycle_state |
| `BugCheckLifecycleEventModel` | `bugcheck_lifecycle_events` | Append-only transition log |
| `BugCheckEnrichmentModel` | `bugcheck_enrichments` | XAI/MAID enrichment artifacts |
| `NeuroForgeRun` | `neuroforge_runs` | LLM run records |
| `ModelResult` | `model_results` | Per-model output |
| `ModelPerformance` | `model_performance` | Benchmark metrics |
| `Inference` | `inferences` | Individual inference records |
| `VibeForgeProject` | `vibeforge_projects` | Project metadata |
| `ProjectSession` | `project_sessions` | Session records |
| `StackOutcome` | `stack_outcomes` | Tech stack analysis results |
| `AuthorForgeProject` | `authorforge_projects` | Book project |
| `Chapter` | `chapters` | Chapter records |
| `Scene` | `scenes` | Scene records |
| `Manuscript` | `manuscripts` | Compiled manuscript blobs |
| `Character` | `characters` | Character definitions |
| `StoryArc` | `story_arcs` | Narrative arc tracking |
| `Location` | `locations` | Setting/place records |
| `SmithyPlanningSession` | `smithy_planning_sessions` | SMITH planning |
| `SmithyPortfolioProject` | `smithy_portfolio` | Portfolio items |
| `SmithyEvaluationSnapshot` | `smithy_evaluations` | Snapshots |
| `Team` | `teams` | Team definitions |
| `TeamMember` | `team_members` | Membership + roles |
| `TeamInvite` | `team_invites` | Pending invitations |
| `TarcieEvent` | `tarcie_events` | DX friction events |
| `BuildGuardEvent` | `buildguard_events` | Quality gate events |
| `DiligenceProject` | `diligence_projects` | Compliance assessment projects |
| `DiligenceFinding` | `diligence_findings` | Assessment findings |
| `DiligenceReview` | `diligence_reviews` | Review records |
| `ModelCatalog` | `model_catalog` | Multi-provider model registry (14 models, 3 tiers) |
| `PricingMonitorRun` | `pricing_monitor_runs` | Pricing monitor agent run records |
| `PricingSnapshot` | `pricing_snapshots` | Point-in-time provider pricing data |
| `PricingAlert` | `pricing_alerts` | Price change / model change alerts |
| `CostLedger` | `cost_ledger` | Per-inference cost records |
| `BatchQueue` | `batch_queue` | Batch inference queue tracking |
| `SentinelSweep` | `sentinel_sweeps` | Health sweep run records (light/deep) |
| `SentinelHealingEvent` | `sentinel_healing_events` | Healing action records with tier + outcome |

### `app/models/schemas.py`
Pydantic v2 schemas (130+) for request/response validation. Each domain has Create, Update, and Response schemas. All schemas use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.

### `app/api/crud.py`
Raw database operations. No business logic. Each function takes a `db: Session` parameter and returns ORM model instances. CRUD functions never raise HTTP exceptions — they return `None` on not-found; routers handle HTTP responses.

### `app/api/search.py`
Implements `hybrid_search()`. Runs vector similarity query (pgvector `<=>` cosine operator) and BM25 full-text query in parallel, then merges via RRF. Returns ranked list of chunks with parent document metadata.

### `app/utils/embeddings.py`
`chunk_text(text, chunk_size, overlap)` — token-aware splitter.
`generate_embedding(text)` — calls Voyage AI with fallback to OpenAI/Cohere.
`process_document(document_id, db)` — orchestrates chunk creation and embedding for a document.

### `alembic/versions/`
13 migration files covering: initial schema, pgvector extension enablement, each major domain addition, field encryption columns, composite indexes, JSONB columns, multi-provider pipeline tables, and Sentinel health sweep tables. Always run `alembic upgrade head` after pulling new code.

---


# §5 — Configuration & Environment Variables

All configuration is injected via environment variables. There are no config files read at runtime beyond `.env` (loaded by the application on startup via `python-dotenv` or equivalent). The canonical reference for all variables is `.env.example` at the repository root.

## Database

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `DATABASE_URL` | str | — | YES | Full PostgreSQL DSN: `postgresql://user:pass@host:port/db` |
| `REDIS_URL` | str | `redis://localhost:6379/0` | YES | Redis connection string; database index 0 |

**Example:**
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
REDIS_URL=redis://localhost:6379/0
```

Never use SQLite in production. The pgvector extension requires PostgreSQL 13+.

## Security & JWT

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `SECRET_KEY` | str | — | YES | 32-char hex minimum. Used for JWT signing and Fernet encryption key derivation |
| `JWT_SECRET_KEY` | str | — | YES | Must equal `SECRET_KEY` in current implementation |
| `ALGORITHM` | str | `HS256` | NO | JWT signing algorithm. Do not change in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `1440` | NO | JWT TTL in minutes (1440 = 24 hours) |

**Generating a secret key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Server

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `HOST` | str | `127.0.0.1` | NO | Bind address. Use `0.0.0.0` in Docker |
| `PORT` | int | `8001` | NO | Listen port. Must not conflict with other Forge services |
| `ALLOWED_ORIGINS` | str | — | YES | Comma-separated CORS origins |

**Example:**
```
HOST=127.0.0.1
PORT=8001
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

In production, `ALLOWED_ORIGINS` must list exact origins. Wildcards are not permitted.

## Embedding & AI Providers

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `VOYAGE_API_KEY` | str | — | YES | Primary embedding provider (voyage.ai) |
| `OPENAI_API_KEY` | str | — | NO | Fallback embedding provider |
| `COHERE_API_KEY` | str | — | NO | Secondary fallback embedding provider |
| `EMBEDDING_MODEL` | str | `voyage-large-2` | NO | Voyage AI model name; 1536-dim output |

**Provider fallback order:** Voyage AI -> OpenAI -> Cohere

If `VOYAGE_API_KEY` is not set, the application will start but embedding generation will fail. All three keys should be configured in production for full resilience.

## Chunking Parameters

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `CHUNK_SIZE` | int | `500` | NO | Token count per chunk |
| `CHUNK_OVERLAP` | int | `50` | NO | Overlapping tokens between adjacent chunks |
| `MAX_EMBEDDING_INPUT_LENGTH` | int | `8000` | NO | Character limit before truncation |

These values are tuned for the Forge corpus. Increasing `CHUNK_SIZE` reduces recall; decreasing it increases storage costs and query latency.

## Logging

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `LOG_LEVEL` | str | `INFO` | NO | Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

Set `LOG_LEVEL=DEBUG` in development only. Debug logging includes embedding inputs and can expose sensitive content.

## OAuth2 / OIDC (Optional)

| Variable | Type | Notes |
|----------|------|-------|
| `GOOGLE_CLIENT_ID` | str | Google OAuth2 app client ID |
| `GOOGLE_CLIENT_SECRET` | str | Google OAuth2 app client secret |
| `GITHUB_CLIENT_ID` | str | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | str | GitHub OAuth app client secret |
| `MICROSOFT_CLIENT_ID` | str | Microsoft Entra (Azure AD) app client ID |
| `MICROSOFT_CLIENT_SECRET` | str | Microsoft Entra app client secret |
| `OAUTH_REDIRECT_URI` | str | Callback URI registered with each provider |

OAuth2 providers are optional. If not configured, those auth flows are unavailable but JWT/API key auth continues to work.

## Rate Limiting

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `RATE_LIMIT_REQUESTS` | int | `100` | Requests per window per user |
| `RATE_LIMIT_WINDOW_SECONDS` | int | `60` | Rate limit window duration |

Rate limits are enforced via Redis token bucket. Global limits apply across all instances.

## Compliance & Encryption

| Variable | Type | Notes |
|----------|------|-------|
| `ENCRYPTION_KEY` | str | AES-256 Fernet key for field-level PII encryption. Derived from `SECRET_KEY` if not set separately |
| `GDPR_DELETION_DELAY_DAYS` | int | Days before hard deletion executes after GDPR erasure request |

## Full `.env.example` Reference

```dotenv
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=<generate-with-secrets.token_hex-32>
JWT_SECRET_KEY=<same-as-SECRET_KEY>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Server
HOST=127.0.0.1
PORT=8001
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# AI Providers
VOYAGE_API_KEY=<from voyage.ai dashboard>
OPENAI_API_KEY=<fallback only>
COHERE_API_KEY=<fallback only>
EMBEDDING_MODEL=voyage-large-2

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_EMBEDDING_INPUT_LENGTH=8000

# Logging
LOG_LEVEL=INFO
```

## Secrets Management

In production, secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `VOYAGE_API_KEY`, etc.) must not live in `.env` files committed to version control. Use:

- **ForgeCommand vault** — the canonical secrets source for Forge services
- **Docker secrets** — for container deployments
- **Kubernetes Secrets** — for k8s deployments (sealed or external-secrets operator)

LLM API keys are synced to DataForge from the ForgeCommand vault via the `/secrets` router. Services retrieve API keys through DataForge at runtime; keys never cross the IPC boundary in plaintext.

---


# §6 — API Layer

DataForge exposes 33 API routers covering 100+ endpoints. All endpoints return JSON. All write endpoints require authentication. The base URL is `http://localhost:8001` in development.

## Authentication Requirements

| Auth Type | Used For |
|-----------|---------|
| JWT Bearer token | User-facing endpoints, admin operations |
| API Key header | Service-to-service calls (NeuroForge, BugCheck, etc.) |
| run_token | BugCheck finding writes, enrichment writes |
| user_token | BugCheck lifecycle transitions (triage, approve, dismiss) |
| No auth | `/health`, `/`, `/metrics` |

## Router Index

### Infrastructure & Health

| Router | Prefix | Key Endpoints |
|--------|--------|--------------|
| Root | `/` | `GET /` — service info and version |
| Health | `/health` | `GET /health` — liveness probe; checks DB + Redis connectivity |
| Metrics | `/metrics` | `GET /metrics` — Prometheus metrics endpoint |

---

### Authentication & Authorization

#### `/auth` — Primary Auth Router
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | JWT login (username + password) |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/auth/oauth/{provider}` | Initiate OAuth2 code flow (google, github, microsoft) |
| `GET` | `/auth/oauth/{provider}/callback` | OAuth2 callback + token exchange |
| `POST` | `/auth/refresh` | Refresh access token |

#### `/auth/mfa` — Multi-Factor Authentication
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/mfa/setup` | Initialize TOTP (returns QR code seed) |
| `POST` | `/auth/mfa/verify` | Verify TOTP code during login |
| `GET` | `/auth/mfa/backup-codes` | Issue 10 backup codes |
| `POST` | `/auth/mfa/backup-codes/use` | Consume a backup code |

#### `/api/v1/auth-secure` — Encrypted Auth
Encrypted variants of auth endpoints for high-security contexts. Request and response bodies use field-level encryption.

#### `/admin/api-keys` — Service API Key Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/api-keys` | Create new service API key |
| `GET` | `/admin/api-keys` | List all active keys |
| `DELETE` | `/admin/api-keys/{key_id}` | Revoke a key |

#### `/admin/token` — Token Operations
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/token` | Issue admin token |
| `POST` | `/admin/token/rotate` | Rotate signing key + invalidate old tokens |

---

### Core Data Access

#### `POST /api/search` — Hybrid Search
Primary search endpoint. Accepts query text, optional domain filter, limit, and similarity threshold. Returns ranked chunks with document metadata.

**Request:**
```json
{
  "query": "string",
  "domain_id": "uuid | null",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

**Response:** Array of `SearchResult` objects with chunk text, document metadata, similarity score, and BM25 rank.

#### `GET /api/search/stats` — Search Statistics
Returns aggregate search usage: total queries, average latency, top domains, cache hit rates.

#### `/admin/documents` — Document Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/documents` | Create document + trigger auto-chunk + embed |
| `GET` | `/admin/documents` | List documents (paginated, filterable by domain/tag) |
| `GET` | `/admin/documents/{id}` | Get document with chunk count |
| `PATCH` | `/admin/documents/{id}` | Update document + re-chunk if content changed |
| `DELETE` | `/admin/documents/{id}` | Delete document + cascade delete chunks |

#### `/admin/domains` — Domain Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/domains` | Create domain |
| `GET` | `/admin/domains` | List all domains |
| `GET` | `/admin/domains/{id}` | Get domain with document count |
| `PATCH` | `/admin/domains/{id}` | Update domain metadata |
| `DELETE` | `/admin/domains/{id}` | Delete domain (fails if documents exist) |

#### `/admin/tags` — Tag Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/tags` | List all tags |
| `POST` | `/admin/tags` | Create tag |

---

### Service Integration Routers

#### `/api/neuroforge` — NeuroForge Integration
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/neuroforge/runs` | Log LLM run |
| `GET` | `/api/neuroforge/runs/{run_id}` | Get run record |
| `POST` | `/api/neuroforge/runs/{run_id}/results` | Log model results |
| `POST` | `/api/neuroforge/inferences` | Log inference record |
| `GET` | `/api/neuroforge/performance` | Query model performance metrics |
| `GET` | `/api/neuroforge/context` | Retrieve relevant context for a query |

#### `/api/vibeforge` — VibeForge Integration
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/vibeforge/projects` | Create project |
| `POST` | `/api/vibeforge/sessions` | Create session |
| `GET` | `/api/vibeforge/sessions/{session_id}` | Get session |
| `POST` | `/api/vibeforge/stack-outcomes` | Record stack analysis outcome |
| `POST` | `/api/vibeforge/code-analysis` | Store code analysis result |

#### `/api/projects` — AuthorForge V2
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/projects` | Create book project |
| `GET` | `/api/projects/{project_id}` | Get project with chapter list |
| `POST` | `/api/projects/{project_id}/chapters` | Create chapter |
| `POST` | `/api/projects/{project_id}/chapters/{chapter_id}/scenes` | Create scene |
| `POST` | `/api/projects/{project_id}/manuscripts` | Compile manuscript |
| `POST` | `/api/projects/{project_id}/characters` | Create character |
| `POST` | `/api/projects/{project_id}/arcs` | Create story arc |
| `POST` | `/api/projects/{project_id}/locations` | Create location |
| `GET` | `/api/projects/{project_id}/knowledge-graph` | Get knowledge graph |

#### `/api/bugcheck` — BugCheck Agent Integration
Full details in §8. Key endpoints:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/bugcheck/runs` | admin token | Create run record (ForgeCommand only) |
| `POST` | `/api/bugcheck/runs/{run_id}/findings` | run_token | Ingest finding |
| `GET` | `/api/bugcheck/runs/{run_id}/findings` | JWT | List findings for run |
| `POST` | `/api/bugcheck/runs/{run_id}/progress` | run_token | Post progress event |
| `POST` | `/api/bugcheck/findings/{finding_id}/lifecycle` | user_token | Transition lifecycle state |
| `POST` | `/api/bugcheck/findings/{finding_id}/enrichments` | run_token | Store enrichment artifact |
| `POST` | `/api/bugcheck/runs/{run_id}/finalize` | admin token | Finalize run (ForgeCommand only) |

#### `/api/agents-registry` — Agent Registry
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agents-registry` | Register agent definition |
| `GET` | `/api/agents-registry` | List all registered agents |
| `GET` | `/api/agents-registry/{agent_id}` | Get agent config |
| `PATCH` | `/api/agents-registry/{agent_id}` | Update agent config |

#### `/forge-runs` — Execution Index
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/forge-runs` | Create execution index record |
| `GET` | `/forge-runs/{run_id}` | Get run status (fast, denormalized) |
| `PATCH` | `/forge-runs/{run_id}` | Update status/outcome |
| `POST` | `/forge-runs/{run_id}/evidence` | Store full evidence blob (JSONB) |
| `GET` | `/forge-runs/{run_id}/evidence` | Retrieve evidence blob |

#### `/api/v1/smithy/planning` — SMITH Planning
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/smithy/planning/sessions` | Create planning session |
| `GET` | `/api/v1/smithy/planning/sessions/{id}` | Get session |
| `PATCH` | `/api/v1/smithy/planning/sessions/{id}` | Update session |

#### `/api/v1/smithy/portfolio` — Portfolio Tracking
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/smithy/portfolio/projects` | Create portfolio project |
| `GET` | `/api/v1/smithy/portfolio/projects` | List projects |
| `POST` | `/api/v1/smithy/portfolio/evaluations` | Store evaluation snapshot |

#### `/api/v1/learning` — Learning Metrics
Stores model performance metrics and surfaces improvement recommendations for NeuroForge.

#### `/api/teams` — Team Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/teams` | Create team |
| `GET` | `/api/teams/{team_id}` | Get team |
| `POST` | `/api/teams/{team_id}/members` | Invite member |
| `PATCH` | `/api/teams/{team_id}/members/{user_id}` | Update member role |
| `DELETE` | `/api/teams/{team_id}/members/{user_id}` | Remove member |
| `GET` | `/api/teams/{team_id}/insights` | Get team insights aggregate |

#### `/api/events` — Immutable Audit Log
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/events` | Append event (HMAC-signed) |
| `GET` | `/api/events` | Query events (filterable, read-only) |

Events are append-only. There is no update or delete endpoint. The HMAC-SHA256 signature on each event enables tamper detection.

#### `/api/v1/model-catalog` — Multi-Provider Model Catalog

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/model-catalog` | List all models (filterable by tier, provider) |
| `GET` | `/api/v1/model-catalog/{model_id}` | Get model details with current pricing |
| `POST` | `/api/v1/model-catalog` | Register a new model |
| `PUT` | `/api/v1/model-catalog/{model_id}` | Update model metadata |
| `DELETE` | `/api/v1/model-catalog/{model_id}` | Remove model from catalog |

#### `/api/v1/pricing` — Pricing Monitoring

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/pricing/snapshots` | List pricing snapshots (filterable by model, date range) |
| `POST` | `/api/v1/pricing/snapshots` | Store a pricing snapshot |
| `GET` | `/api/v1/pricing/alerts` | List pricing alerts (filterable by status, type) |
| `POST` | `/api/v1/pricing/alerts` | Create a pricing alert |
| `PATCH` | `/api/v1/pricing/alerts/{alert_id}` | Acknowledge or update an alert |
| `GET` | `/api/v1/pricing/runs` | List pricing monitor runs |
| `POST` | `/api/v1/pricing/runs` | Record a pricing monitor run |
| `PATCH` | `/api/v1/pricing/runs/{run_id}` | Update run status |

#### `/api/v1/cost-ledger` — Cost Tracking

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/cost-ledger` | Record a cost entry (per-inference) |
| `GET` | `/api/v1/cost-ledger` | Query cost entries (filterable by run, model, provider, date range) |
| `GET` | `/api/v1/cost-ledger/aggregations` | Aggregated cost data (by provider, by model, by period) |

#### `/api/v1/sentinel` — Sentinel Health Sweeps & Healing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sentinel/sweeps` | Create a sweep record |
| `GET` | `/api/v1/sentinel/sweeps` | List sweeps (filterable by type, status) |
| `GET` | `/api/v1/sentinel/sweeps/{sweep_id}` | Get sweep details with dimension results |
| `PATCH` | `/api/v1/sentinel/sweeps/{sweep_id}` | Update sweep status/findings |
| `POST` | `/api/v1/sentinel/healing` | Record a healing event |
| `GET` | `/api/v1/sentinel/healing` | List healing events (filterable by tier, outcome) |
| `GET` | `/api/v1/sentinel/healing/{event_id}` | Get healing event details |
| `PATCH` | `/api/v1/sentinel/healing/{event_id}` | Update healing event status |

---

### Infrastructure Routers

| Router | Prefix | Purpose |
|--------|--------|---------|
| Tracing | `/api/tracing` | OpenTelemetry span ingestion |
| Deployment | `/api-deployment` | Load balancer, instance health, graceful drain |
| Cache | `/cache` | Redis cache sync operations |
| Cache Replication | `/cache-replication` | Cache failover management |
| Secrets | `/secrets` | LLM API key vault (synced from ForgeCommand) |
| Diligence | `/api/diligence` | Security/compliance assessment |
| Rate Limiting | `/rate-limit` | Distributed rate limit management |
| FPVS | `/fpvs` | FPVS Phase 1 endpoints |
| Tarcie | `/tarcie` | DX friction event capture |
| DLQ | `/dlq` | Dead letter queue inspection + replay |

#### `/admin-ui` — Admin Interface
`GET /admin-ui` serves the Jinja2-rendered admin HTML template. Provides a browser-based interface for document management, search testing, and domain administration. No JavaScript framework required.

---


# §7 — Backend Internals

## Vector Search Engine

### Overview

The hybrid search engine (`app/api/search.py`) runs two retrieval passes in parallel and merges them via Reciprocal Rank Fusion (RRF). Neither pass is optional — both run on every search request.

### Pass 1: Semantic (Vector) Retrieval

```python
# pgvector cosine similarity query
results = db.execute(
    select(Chunk, Document)
    .join(Document)
    .where(
        (1 - Chunk.embedding.cosine_distance(query_vector)) >= similarity_threshold
    )
    .order_by(Chunk.embedding.cosine_distance(query_vector))
    .limit(limit * 3)  # Over-fetch for RRF merging
)
```

The `<=>` operator (cosine distance) is provided by pgvector. Lower cosine distance = higher similarity. The complement `(1 - distance)` gives similarity in [0, 1].

### Pass 2: BM25 Full-Text Retrieval

```python
# PostgreSQL TSVECTOR + ts_rank
results = db.execute(
    select(Chunk, Document)
    .join(Document)
    .where(
        Chunk.tsvector.op('@@')(func.plainto_tsquery('english', query_text))
    )
    .order_by(
        func.ts_rank(Chunk.tsvector, func.plainto_tsquery('english', query_text)).desc()
    )
    .limit(limit * 3)
)
```

`TSVECTOR` columns are maintained by PostgreSQL triggers on insert/update. `plainto_tsquery` handles stopword removal and stemming automatically.

### RRF Merge

```python
def reciprocal_rank_fusion(semantic_results, bm25_results, k=60):
    scores = {}
    for rank, chunk_id in enumerate(semantic_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    for rank, chunk_id in enumerate(bm25_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

`k=60` is the standard RRF constant. A chunk appearing in both result sets gets double contribution. Chunks that rank highly in both get the highest merged scores.

---

## Embedding Pipeline

### Chunking

`app/utils/embeddings.py` implements token-aware chunking:

```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    # Uses a tokenizer-aware splitter
    # Respects sentence boundaries where possible
    # Returns list of overlapping text segments
```

**Token counting:** Uses the same tokenizer as the target embedding model (Voyage AI uses a BPE tokenizer compatible with tiktoken's `cl100k_base`).

**Overlap behavior:** Each chunk shares the last `overlap` tokens with the next chunk. This prevents important context from being split across chunk boundaries and lost during retrieval.

### Embedding Generation

```python
async def generate_embedding(text: str) -> list[float]:
    if len(text) > MAX_EMBEDDING_INPUT_LENGTH:
        text = text[:MAX_EMBEDDING_INPUT_LENGTH]

    try:
        response = voyage_client.embed([text], model=EMBEDDING_MODEL)
        return response.embeddings[0]
    except VoyageError:
        # Fallback to OpenAI
        try:
            response = openai_client.embeddings.create(
                input=text, model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except OpenAIError:
            # Fallback to Cohere
            response = cohere_client.embed(texts=[text])
            return response.embeddings[0]
```

Embeddings are generated synchronously per chunk during document processing. For batch operations (bulk import), chunks are embedded in parallel up to the provider's rate limit.

### Auto-Processing Trigger

When a document is created or its `content` field is updated via `POST /admin/documents` or `PATCH /admin/documents/{id}`, the API layer calls `process_document(document_id, db)` before returning the response. This ensures embeddings are always current when the endpoint returns.

---

## Field-Level Encryption

### AES-256 Fernet

DataForge encrypts PII fields automatically using `cryptography.fernet.Fernet`. The encryption key is derived from `SECRET_KEY`.

**Models with encrypted fields:**
- `User` — `email` (PII)
- `TeamMember` — contact fields
- `DiligenceProject` — assessment subject details
- Additional models as annotated in `models.py`

### Encryption Mechanism

```python
from cryptography.fernet import Fernet

class EncryptedField(TypeDecorator):
    """SQLAlchemy custom type that transparently encrypts/decrypts."""
    impl = LargeBinary

    def process_bind_param(self, value, dialect):
        # Encrypt before write
        if value is not None:
            return fernet.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value, dialect):
        # Decrypt after read
        if value is not None:
            return fernet.decrypt(value.encode()).decode()
        return value
```

Encryption/decryption is transparent at the ORM layer. Application code reads and writes plaintext; the `EncryptedField` type handles the transformation. Encrypted values in PostgreSQL are stored as `TEXT` (base64-encoded Fernet tokens).

**Key rotation:** Requires a migration to re-encrypt all existing records with the new key. A key rotation script is provided in `scripts/`.

---

## Anomaly Detection

DataForge implements six threat detection patterns in the auth layer, evaluated on every authentication event:

### Detection Types

| Type | Trigger | Response |
|------|---------|---------|
| **Impossible travel** | Login from geographically impossible location within time window | Block + audit event |
| **Brute force** | >5 failed login attempts within 5 minutes | Account lockout (15 min) + audit event |
| **Bulk exfiltration** | >1000 document reads in <60 seconds from single user | Rate limit + audit event + alert |
| **Suspicious access** | Access to high-sensitivity domains outside normal hours | Audit event + optional MFA challenge |
| **After-hours access** | Admin operations outside configured business hours | Audit event |
| **Bulk mutations** | >100 writes in <60 seconds from single user | Rate limit + audit event |

### Implementation

Each detection type runs as an async check after the primary auth validation succeeds. Detection results are written to the audit log via `POST /api/events`. The auth response is returned to the caller only after all anomaly checks complete (detections are non-blocking for legitimate users; blocking only on hard violations like brute force).

---

## Rate Limiting

DataForge uses a distributed Redis token bucket:

```
Per request:
  1. GET rate_limit:{user_id} from Redis
  2. If tokens < 1: return 429 Too Many Requests
  3. Decrement token count
  4. Set expiry if key is new (window reset)

Refill:
  Background task refills tokens at RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW_SECONDS
```

Global limits apply across all DataForge instances. A single user cannot circumvent limits by hitting different instances.

---

## Audit Log

Every significant event — auth successes, failures, anomaly detections, lifecycle transitions, admin operations — is written to the audit log:

```python
event = AuditEvent(
    event_type="finding.lifecycle.transition",
    actor_id=user_id,
    resource_type="bugcheck_finding",
    resource_id=finding_id,
    payload={"from": "NEW", "to": "TRIAGED"},
    timestamp=utcnow(),
    hmac=hmac_sha256(event_data, SECRET_KEY)
)
```

The `hmac` field enables tamper detection. On audit log export or compliance review, each event's HMAC is re-computed and compared. Any mismatch indicates tampering.

**The audit log table has no UPDATE or DELETE operations in the ORM.** The only permitted operation is INSERT. The `/api/events` router has no PATCH or DELETE endpoints.

---

## Dead Letter Queue (DLQ)

Async tasks that fail after 3 retries (exponential backoff, max 60 seconds) are written to the DLQ table. The `/dlq` router provides:

- `GET /dlq` — list failed tasks with error context
- `POST /dlq/{task_id}/replay` — manually replay a failed task
- `DELETE /dlq/{task_id}` — discard a failed task (requires admin)

DLQ entries include the full task payload, error traceback, retry count, and timestamps for each attempt. This is the recovery path for embedding failures, cache sync failures, and notification failures.

---

## CORS Configuration

CORS is configured in `app/main.py` via FastAPI's `CORSMiddleware`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Run-Token"],
)
```

`allow_credentials=True` is required for JWT cookie flows. The `X-Run-Token` header is the BugCheck scoped run token. Wildcards in `allow_origins` are rejected in production builds via a startup assertion.

---


# §8 — Ecosystem Integration Contracts

This section defines the integration contract between DataForge and each Forge service. Each service has exactly defined authorization scope, write permissions, and prohibited operations.

## Integration Principles

1. **Every service authenticates.** No endpoint accepts unauthenticated writes.
2. **Scope is enforced, not suggested.** A service attempting to write outside its authorized scope receives 403 Forbidden.
3. **DataForge is the record.** Services may cache reads locally for performance but must never treat their cache as authoritative.
4. **Fail loudly.** When DataForge is unavailable, services must fail, not degrade silently.

---

## BugCheck Agent

BugCheck is the most tightly governed integration. The access control matrix is enforced at the API layer.

### Access Control Matrix

| Component | Authorized Writes | Auth Token Required |
|-----------|------------------|-------------------|
| ForgeCommand | run records, lifecycle transitions, run finalization | admin token |
| BugCheck Agent | findings, progress events, check telemetry | run_token (scoped) |
| XAI (Grok) | enrichment artifacts only | run_token |
| MAID (Claude) | enrichment artifacts only | run_token |
| VibeForge | user decisions (lifecycle transitions) only | user_token |

### run_token Contract

```
run_token = JWT signed with SECRET_KEY
Claims:
  - run_id: UUID (exact match required)
  - targets: list[str] (exact match required)
  - mode: "quick" | "standard" | "deep"
  - scope: "changed_files" | "package" | "full_repo"
  - commit_sha: str (exact match required)
  - nonce: str (replay protection, single-use)
  - iat: int
  - exp: int (iat + 1800 to iat + 3600)
```

A run_token is bound to its run. A BugCheck agent with a valid run_token for run A cannot write findings to run B. The nonce prevents replay attacks — each token is single-use for write operations.

### Finding Ingestion Flow

```
BugCheck Agent
    │
    ├── POST /api/bugcheck/runs/{run_id}/findings
    │   Headers: Authorization: Bearer {run_token}
    │   Body: FindingCreate schema
    │   │
    │   └── DataForge validates:
    │       1. run_token signature + expiry
    │       2. run_token.run_id == path run_id
    │       3. Run status is "running" (not finalized)
    │       4. Finding fingerprint uniqueness
    │       5. Severity + category enum membership
    │       │
    │       └── Writes BugCheckFindingModel
    │           lifecycle_state = "NEW"
    │           autofix_available = False (updated by enrichment)
    │           created_at = utcnow()
```

### Lifecycle Transition Flow

```
VibeForge (user decision)
    │
    ├── POST /api/bugcheck/findings/{finding_id}/lifecycle
    │   Headers: Authorization: Bearer {user_token}
    │   Body: { "to_state": "TRIAGED", "reason": "..." }
    │   │
    │   └── DataForge validates:
    │       1. user_token signature + expiry
    │       2. Transition is valid (see §9 state machine)
    │       3. Finding is not in terminal state
    │       │
    │       └── Writes BugCheckLifecycleEventModel (append-only)
    │           Updates BugCheckFindingModel.lifecycle_state
```

**Invariants:**
- BugCheck Agent NEVER writes lifecycle transitions.
- VibeForge NEVER writes findings.
- After a run is finalized (status = "finalized"), POST to findings returns 409.

### Severity Levels

| Level | Name | Gating Behavior |
|-------|------|----------------|
| S0 | Release Blocker | Blocks all merges and deployments |
| S1 | High | Blocks PR merge |
| S2 | Medium | Warning only, no block |
| S3 | Low | Informational |
| S4 | Info | Advisory only |

---

## NeuroForge

NeuroForge logs all LLM run state to DataForge. It never maintains its own authoritative run history.

### Integration Points

| Operation | DataForge Endpoint | Writes |
|-----------|-------------------|--------|
| Log run start | `POST /api/neuroforge/runs` | NeuroForgeRun record |
| Log model results | `POST /api/neuroforge/runs/{run_id}/results` | ModelResult records |
| Log performance | `POST /api/neuroforge/runs/{run_id}/performance` | ModelPerformance record |
| Log inference | `POST /api/neuroforge/inferences` | Inference record |
| Retrieve context | `GET /api/neuroforge/context?query=...` | Read-only |

Context retrieval uses the hybrid search engine to find relevant document chunks for the query. NeuroForge uses this to build RAG context before LLM inference.

**Auth:** NeuroForge uses service API keys. No run_token scoping applies.

---

## VibeForge

VibeForge persists all project-level state and code analysis results.

### Integration Points

| Operation | DataForge Endpoint | Writes |
|-----------|-------------------|--------|
| Create project | `POST /api/vibeforge/projects` | VibeForgeProject |
| Create session | `POST /api/vibeforge/sessions` | ProjectSession |
| Log stack outcome | `POST /api/vibeforge/stack-outcomes` | StackOutcome |
| Store code analysis | `POST /api/vibeforge/code-analysis` | Analysis result |
| BugCheck decisions | `POST /api/bugcheck/findings/{id}/lifecycle` | Lifecycle transition only |

**Auth:** VibeForge uses service API keys for project/session writes. For BugCheck lifecycle transitions, it uses a user_token issued on behalf of the authenticated user.

---

## AuthorForge V2

AuthorForge is the most content-intensive integration. All narrative content — including manuscripts that may exceed 100k tokens — is persisted to DataForge.

### Integration Points

| Resource | Endpoint Pattern | Notes |
|----------|-----------------|-------|
| Projects | `/api/projects` | Book-level metadata |
| Chapters | `/api/projects/{id}/chapters` | Ordered chapter list |
| Scenes | `/api/projects/{id}/chapters/{id}/scenes` | Scene text + metadata |
| Characters | `/api/projects/{id}/characters` | Character definitions |
| Story Arcs | `/api/projects/{id}/arcs` | Narrative arc tracking |
| Locations | `/api/projects/{id}/locations` | Setting definitions |
| Knowledge Graph | `/api/projects/{id}/knowledge-graph` | Relationship graph |
| Manuscripts | `/api/projects/{id}/manuscripts` | Compiled full manuscript |

**Chunking:** Scene and chapter content is automatically chunked and embedded on write. This enables semantic search across all narrative content within a project.

**Auth:** Service API keys.

---

## ForgeAgents

ForgeAgents (the agent runtime) uses DataForge for agent configuration persistence and execution record keeping.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Register agent | `POST /api/agents-registry` |
| Get agent config | `GET /api/agents-registry/{agent_id}` |
| Log execution | `POST /forge-runs` |
| Update execution status | `PATCH /forge-runs/{run_id}` |
| Store evidence | `POST /forge-runs/{run_id}/evidence` |

**Auth:** Admin token for registry writes. Service API key for run logging.

---

## ForgeCommand

ForgeCommand is the orchestration plane. It has elevated privileges:

### Exclusive Operations (admin token only)

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create BugCheck run | `POST /api/bugcheck/runs` |
| Finalize BugCheck run | `POST /api/bugcheck/runs/{id}/finalize` |
| Write lifecycle transitions | (via ForgeCommand authority) |
| Token rotation | `POST /admin/token/rotate` |
| API key management | `POST /admin/api-keys` |
| Secrets sync | `POST /secrets` (sync from ForgeCommand vault) |

**ForgeCommand is the only component authorized to finalize runs.** BugCheck agent cannot self-finalize.

---

## Forge:SMITH

SMITH uses DataForge for planning sessions, portfolio tracking, and evaluation snapshots.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create planning session | `POST /api/v1/smithy/planning/sessions` |
| Update session | `PATCH /api/v1/smithy/planning/sessions/{id}` |
| Create portfolio project | `POST /api/v1/smithy/portfolio/projects` |
| Store evaluation snapshot | `POST /api/v1/smithy/portfolio/evaluations` |
| Log governance events | `POST /api/events` |

Governance events written by SMITH to the audit log are HMAC-signed and immutable. SMITH reads run state from `/forge-runs` for its authority layer operations.

**Auth:** Service API key. Governance event writes use a dedicated SMITH service key with elevated signing privileges.

---

## Teams

The Teams subsystem is service-agnostic; any Forge service can query team membership and insights.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create team | `POST /api/teams` |
| Add member | `POST /api/teams/{id}/members` |
| Query insights | `GET /api/teams/{id}/insights` |
| Update member role | `PATCH /api/teams/{id}/members/{user_id}` |

---

## Sentinel Agent

The Sentinel Agent monitors ecosystem health and performs autonomous healing. It uses DataForge to persist sweep results and healing event records.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create sweep | `POST /api/v1/sentinel/sweeps` |
| Update sweep | `PATCH /api/v1/sentinel/sweeps/{sweep_id}` |
| Record healing | `POST /api/v1/sentinel/healing` |
| Update healing | `PATCH /api/v1/sentinel/healing/{event_id}` |
| Query sweep history | `GET /api/v1/sentinel/sweeps` |

**Auth:** Service API key. Healing events at Tier B require ForgeCommand approval metadata.

**Sweep Types:**
- **Light sweep** (D1+D3+D6): Runs every 5 minutes, <10s execution
- **Deep sweep** (D1-D6): On-demand or triggered by anomaly, 30-60s execution

---

## Pricing Monitor Agent

The Pricing Monitor Agent periodically scrapes provider pricing pages and compares against stored catalog data.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Fetch model catalog | `GET /api/v1/model-catalog` |
| Store pricing snapshot | `POST /api/v1/pricing/snapshots` |
| Create pricing alert | `POST /api/v1/pricing/alerts` |
| Record monitor run | `POST /api/v1/pricing/runs` |
| Update run status | `PATCH /api/v1/pricing/runs/{run_id}` |

**Auth:** Service API key. Alert types: PRICE_INCREASE, PRICE_DECREASE, NEW_MODEL, MODEL_DEPRECATED, CAPABILITY_CHANGE.

---

## Common Integration Patterns

### Health Check Before Run Start

Every service that starts a long-running operation MUST verify DataForge availability first:

```python
async def check_dataforge_health() -> bool:
    try:
        response = await http_client.get(
            "http://localhost:8001/health",
            timeout=5.0
        )
        return response.status_code == 200
    except (httpx.TimeoutException, httpx.ConnectError):
        return False

if not await check_dataforge_health():
    raise DataForgeUnavailableError("DataForge health check failed; run aborted")
```

### Structured Error Handling

```python
class DataForgeError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"DataForge returned {status_code}: {detail}")

# In service code:
response = await dataforge_client.post(...)
if response.status_code == 409:
    raise DataForgeError(409, response.json()["detail"])
elif response.status_code >= 500:
    raise DataForgeUnavailableError(f"DataForge server error: {response.status_code}")
```

### Audit Event Pattern

All significant cross-service operations should produce an audit event:

```python
await dataforge_client.post(
    "/api/events",
    json={
        "event_type": "bugcheck.finding.created",
        "actor_id": run_id,
        "resource_type": "bugcheck_finding",
        "resource_id": str(finding_id),
        "payload": {"severity": "S1", "category": "security"}
    }
)
```

---


# §9 — Error Handling, Lifecycle & Access Control

## BugCheck Finding Lifecycle State Machine

The lifecycle state machine is the most critical behavioral contract DataForge enforces. It is implemented at the API layer, not as advisory logic.

### States

| State | Description |
|-------|-------------|
| `NEW` | Finding just ingested, no human review yet |
| `TRIAGED` | Reviewed and classified by a human |
| `FIX_PROPOSED` | MAID/XAI has generated a fix proposal |
| `APPROVED` | Fix approved by authorized user |
| `APPLIED` | Fix has been applied to the codebase |
| `VERIFIED` | Applied fix confirmed correct by re-run |
| `CLOSED` | Finding resolved and archived |
| `DISMISSED` | Finding explicitly dismissed (requires reason + scope + expiration) |

### Valid Transitions

```
NEW ──────────────────────────────────────────────► DISMISSED
 │
 └──► TRIAGED ──────────────────────────────────────► DISMISSED
          │
          └──► FIX_PROPOSED ──────────────────────────► DISMISSED
                    │
                    └──► APPROVED
                              │
                              └──► APPLIED
                                       │
                                       └──► VERIFIED
                                                │
                                                └──► CLOSED
```

**DISMISSED** is reachable from any non-terminal state. `CLOSED` and `DISMISSED` are terminal states — no transitions out.

### Invalid Transitions (return 409 Conflict)

Any transition not in the valid set above returns `409 Conflict`. Examples:

| Attempted Transition | Response |
|---------------------|---------|
| `NEW -> APPROVED` | 409 — must pass through TRIAGED |
| `NEW -> APPLIED` | 409 — multiple steps skipped |
| `VERIFIED -> NEW` | 409 — backward transition |
| `CLOSED -> TRIAGED` | 409 — terminal state |
| `DISMISSED -> FIX_PROPOSED` | 409 — terminal state |
| `APPLIED -> TRIAGED` | 409 — backward transition |

### DISMISSED Requirements

The `DISMISSED` state requires three additional fields in the transition payload:

```json
{
  "to_state": "DISMISSED",
  "reason": "false_positive — test fixture intentionally triggers this pattern",
  "scope": "file",
  "expiration": "2026-12-31T00:00:00Z"
}
```

| Field | Type | Constraint |
|-------|------|-----------|
| `reason` | str | Required, minimum 10 characters |
| `scope` | enum | `file` \| `function` \| `project` \| `global` |
| `expiration` | datetime | Required, must be future date |

Dismissals without these fields return `422 Unprocessable Entity`.

### Run Immutability After Finalization

When a run transitions to `status = "finalized"`:

- All subsequent `POST /api/bugcheck/runs/{run_id}/findings` return **409 Conflict**
- All subsequent `POST /api/bugcheck/runs/{run_id}/progress` return **409 Conflict**
- The run record becomes read-only
- Existing findings retain their lifecycle states and continue to accept transitions

This is enforced in the finding ingestion endpoint:

```python
run = db.get(BugCheckRunModel, run_id)
if run is None:
    raise HTTPException(404, "Run not found")
if run.status == "finalized":
    raise HTTPException(409, "Run is finalized; new findings rejected")
```

---

## HTTP Status Code Reference

| Code | Meaning in DataForge Context |
|------|------------------------------|
| `200 OK` | Successful GET, PATCH |
| `201 Created` | Successful POST (resource created) |
| `204 No Content` | Successful DELETE |
| `400 Bad Request` | Malformed request body (JSON parse error) |
| `401 Unauthorized` | Missing or invalid auth token |
| `403 Forbidden` | Valid auth, but insufficient scope/permissions |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Invalid lifecycle transition, run finalized, duplicate fingerprint |
| `422 Unprocessable Entity` | Valid JSON but fails schema validation (Pydantic) |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unexpected server fault |
| `503 Service Unavailable` | PostgreSQL or Redis unavailable |

---

## Access Control Enforcement

### Token Validation Flow

Every protected endpoint runs this validation before business logic:

```
Request arrives
    │
    ├── Extract token from Authorization header
    │   (Bearer {token} or X-API-Key {key} or X-Run-Token {token})
    │
    ├── Validate signature (HMAC or JWT)
    │
    ├── Check expiry
    │
    ├── Check token type matches endpoint requirements
    │   (run_token ≠ user_token ≠ API key ≠ admin JWT)
    │
    ├── For run_token: validate run_id claim matches path parameter
    │
    └── For run_token: validate nonce (not replayed)
```

Any failure at any step returns 401 or 403 with no further processing.

### Scope Violations

| Attempted Action | Actor | Response |
|-----------------|-------|---------|
| BugCheck writes lifecycle transition | BugCheck (run_token) | 403 |
| VibeForge writes finding | VibeForge (user_token) | 403 |
| BugCheck finalizes run | BugCheck (run_token) | 403 |
| XAI writes finding | XAI (run_token) | 403 (enrichment endpoint only) |
| Any service rotates tokens | Non-admin | 403 |

These are **system faults**, not user errors. They are logged as security events in the audit log with the actor's token claims and the attempted operation.

---

## Duplicate Fingerprint Handling

Every finding has a `fingerprint` field that is stable across runs for the same logical issue. Fingerprints are computed by the BugCheck agent:

```python
# Default fingerprint
fingerprint = sha256(f"{category}:{rule_id}:{file_path}:{line_range}:{normalized_message}")

# Category-specific fingerprints
# API Contract Drift:
fingerprint = sha256(f"{service}:{schema_path}:{field_name}:{change_type}")
# Dependency CVE:
fingerprint = sha256(f"{package_name}:{version_range}:{cve_id}")
# Flaky Test:
fingerprint = sha256(f"{test_file}:{test_name}:{failure_signature}")
```

On ingestion, DataForge checks for an existing finding with the same `fingerprint` in any prior run for the same service. If found, it associates the new finding with the existing record via `correlation_id` rather than creating a duplicate. This enables trending and deduplication across runs.

---

## Error Response Format

All DataForge error responses follow FastAPI's standard format:

```json
{
  "detail": "Human-readable description of the error"
}
```

For validation errors (422), the format includes field-level detail:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "reason"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

---

## Graceful Degradation Policy

DataForge does not degrade silently. When dependencies are unavailable:

| Dependency | Behavior |
|-----------|---------|
| PostgreSQL down | All endpoints return 503; liveness probe returns 503 |
| Redis down | Rate limiting disabled (safe fail-open); cache misses on all reads; Redis-dependent endpoints return 503 |
| Embedding provider down | Document write returns 202 (accepted); chunking queued for retry; search returns existing results without new document |
| Celery down | Async tasks queued in DLQ; synchronous path used as fallback where possible |

**Safe fail-open exceptions:** Rate limiting only. All auth checks fail-closed (deny if auth dependency is unavailable).

---

## Compliance Deletion (GDPR / CCPA)

When a GDPR erasure request is received:

1. User record is soft-deleted (anonymized, not hard-deleted) immediately
2. Hard deletion is scheduled after `GDPR_DELETION_DELAY_DAYS` (default: 30)
3. All associated documents are anonymized (author field scrubbed)
4. Audit log entries are retained but actor identity is pseudonymized
5. Encrypted field values are re-encrypted with a null key (effectively zeroed)

The compliance test suite (`tests/test_compliance_gdpr.py`) verifies this full flow.

---


# §10 — Testing

## Overview

| Metric | Value |
|--------|-------|
| Total test files | 32 |
| Total tests | 296 |
| Passing | 296/296 (100%) |
| Coverage | 82% |

## Test Pyramid

### Unit Tests

Target individual functions and classes with no database or network I/O. Use `pytest-mock` for dependency injection.

| Test File | Coverage Area |
|-----------|--------------|
| `test_auth.py` | JWT creation, validation, expiry, bcrypt hashing |
| `test_encryption.py` | Fernet field encryption/decryption, key rotation |
| `test_rate_limiting.py` | Token bucket logic, window reset, burst handling |
| `test_anomaly_detection.py` | All 6 detection types, threshold boundaries |
| `test_embeddings.py` | Chunking logic, overlap correctness, truncation |
| `test_rrf.py` | Reciprocal rank fusion merge correctness |
| `test_fingerprint.py` | Fingerprint stability across equivalent inputs |
| `test_lifecycle.py` | State machine transitions (valid + invalid) |
| `test_schemas.py` | Pydantic schema validation, edge cases |

### Integration Tests

Require live PostgreSQL and Redis connections. Run against a test database (separate from dev). Use fixtures to set up and tear down state.

| Test File | Coverage Area |
|-----------|--------------|
| `test_search_integration.py` | Full hybrid search pipeline end-to-end |
| `test_admin_api.py` | Document CRUD + auto-chunking trigger |
| `test_neuroforge_api.py` | NeuroForge router: run logging, inference, context |
| `test_vibeforge_api.py` | VibeForge router: projects, sessions, outcomes |
| `test_authorforge_api.py` | AuthorForge V2: full content hierarchy |
| `test_bugcheck_api.py` | BugCheck router: finding ingestion, lifecycle |
| `test_bugcheck_access_control.py` | Scope enforcement, invalid token types |
| `test_teams_api.py` | Team management, member RBAC |
| `test_agents_registry.py` | Agent registration and retrieval |
| `test_smithy_api.py` | Planning sessions, portfolio, evaluations |
| `test_cache_failover.py` | Redis sentinel failover simulation |
| `test_db_failover.py` | PostgreSQL replica failover simulation |
| `test_dlq.py` | Dead letter queue write + replay |

### Security Tests

| Test File | Coverage Area |
|-----------|--------------|
| `test_auth_security.py` | OAuth2 flows, TOTP 2FA, backup codes |
| `test_jwt_security.py` | Token forgery, expiry bypass, algorithm confusion |
| `test_run_token.py` | run_token scope enforcement, nonce replay protection |
| `test_api_key_security.py` | Key revocation, scope isolation |

### Compliance Tests

| Test File | Coverage Area |
|-----------|--------------|
| `test_compliance_gdpr.py` | Erasure flow, soft delete, hard delete scheduling |
| `test_compliance_encryption.py` | PII field encryption in stored records |
| `test_audit_log.py` | HMAC integrity, append-only enforcement |

### E2E Tests

Full workflow tests that exercise multiple routers in sequence, simulating real service interactions.

| Test File | Coverage Area |
|-----------|--------------|
| `test_e2e_bugcheck_run.py` | Full BugCheck run: create -> findings -> lifecycle -> finalize |
| `test_e2e_neuroforge_workflow.py` | LLM run -> results -> performance -> context retrieval |
| `test_e2e_authorforge_project.py` | Book -> chapters -> scenes -> manuscript compilation |

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### With Coverage
```bash
pytest --cov=app tests/ --cov-report=term-missing
```

### Specific Domain
```bash
pytest tests/test_bugcheck_api.py -v
pytest tests/test_bugcheck_access_control.py -v
```

### Security Tests Only
```bash
pytest tests/test_auth_security.py tests/test_run_token.py tests/test_jwt_security.py -v
```

### Compliance Tests Only
```bash
pytest tests/test_compliance_gdpr.py tests/test_audit_log.py -v
```

## Test Configuration

`pytest.ini` at repository root:

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts = --strict-markers -q
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (requires PostgreSQL + Redis)
    security: Security and auth tests
    compliance: Compliance and audit tests
    e2e: End-to-end workflow tests
    slow: Tests that take >1 second
```

### Test Database Setup

Integration tests require a separate PostgreSQL database:

```bash
# Create test database
createdb dataforge_test

# Run migrations against test DB
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge_test \
  alembic upgrade head

# Run integration tests
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge_test \
  pytest tests/ -m integration -v
```

The test database is fully migrated before each test session. Individual test functions use transactions that are rolled back after each test (no persistent state leaks between tests).

### Fixtures

Key fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def db_session():
    """Provides a rollback-isolated database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """FastAPI test client with overridden database dependency."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token(client):
    """Creates an admin user and returns a valid JWT."""
    # ... creates user, logs in, returns token

@pytest.fixture
def run_token():
    """Returns a valid scoped run_token for test run."""
    # ... generates run_token with test run_id
```

## Coverage Targets

| Area | Current | Target |
|------|---------|--------|
| Overall | 82% | 85%+ |
| Auth module | 95% | 95%+ |
| BugCheck router | 90% | 90%+ |
| Lifecycle state machine | 100% | 100% |
| Search engine | 88% | 88%+ |
| Encryption utilities | 92% | 92%+ |
| Admin router | 78% | 85%+ |
| Domain-specific routers | 74% | 80%+ |

Lines currently not covered: error recovery branches in database failover simulation, some OAuth2 provider edge cases, and k6 load test infrastructure.

## Load Testing (Optional)

k6 scripts are available for load testing but are not part of the standard CI pipeline:

```bash
# Install k6
# Run against local instance
k6 run scripts/load_test_search.js
k6 run scripts/load_test_ingestion.js
```

Target: sustain 1,000 RPS at p95 < 100ms with a test corpus of 100,000 chunks.

---


# §11 — Handover, Critical Constraints & Migration Runbook

## Critical Invariants — Never Violate These

These are architectural invariants, not guidelines. Violating them causes data loss, security breaches, or ecosystem-wide consistency failures.

### 1. DataForge Is the Only Source of Truth

No service maintains authoritative state outside DataForge. There is no "eventually consistent" model. There is no "local cache that syncs later." If DataForge is unavailable, the operation does not happen. Period.

```
WRONG: Service stores finding in local DB, syncs to DataForge later
RIGHT: Service attempts DataForge write; if it fails, the operation fails
```

### 2. run_token Scope Cannot Be Widened

A run_token issued for `run_id=abc` cannot be used to write findings to `run_id=xyz`. The DataForge API validates the `run_id` claim in the token against the path parameter on every request. Do not attempt to "share" tokens across runs.

### 3. Lifecycle Transitions Are One-Way (With One Exception)

Once a finding reaches a terminal state (`CLOSED` or `DISMISSED`), no further transitions are possible. The only "reset" path is to re-run BugCheck — which produces new findings, not new states on old ones.

### 4. The Audit Log Is Append-Only Forever

There is no admin endpoint to delete audit log entries. There is no SQL DELETE on the events table in any migration. If you find code attempting to DELETE from the audit log, treat it as a security incident.

### 5. After FINALIZED, Run Records Are Immutable

The `status = "finalized"` transition is one-way. ForgeCommand sets it; nothing can unset it. Attempts to write findings to a finalized run return 409. This is by design — finalization is a commitment to the record.

### 6. Field Encryption Key Rotation Requires a Migration

Changing `SECRET_KEY` (and thus the derived Fernet key) without a migration script will make all existing encrypted field values unreadable. Never rotate the secret key without running the re-encryption migration first. The migration script is at `scripts/rotate_encryption_key.py`.

---

## Access Control Quick Reference

| Actor | Can Write | Cannot Write |
|-------|-----------|-------------|
| ForgeCommand (admin token) | Run records, lifecycle transitions, finalization, API keys, tokens | Findings, enrichments |
| BugCheck Agent (run_token) | Findings, progress events, check telemetry | Lifecycle transitions, run records |
| XAI/MAID (run_token) | Enrichment artifacts | Findings, lifecycle transitions, run records |
| VibeForge (user_token) | User decisions (lifecycle transitions) | Findings, run records, enrichments |
| NeuroForge (API key) | Run results, inference records, performance metrics | BugCheck data |
| AuthorForge (API key) | Project content hierarchy | BugCheck data, run records |
| SMITH (API key) | Planning sessions, portfolio, governance events | BugCheck findings |
| Sentinel (API key) | Sweep records, healing events | BugCheck data, run records |
| Pricing Monitor (API key) | Pricing snapshots, alerts, monitor runs | BugCheck data |
| Any service | Audit events (append-only) | Modify/delete audit events |

---

## Migration Runbook

### Standard Post-Pull Procedure

After pulling new DataForge code:

```bash
cd /home/charlie/Forge/ecosystem/DataForge

# 1. Activate virtualenv
source venv/bin/activate

# 2. Install any new dependencies
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Verify migrations applied cleanly
alembic current

# 5. Run tests to confirm nothing broken
pytest tests/ -v --tb=short

# 6. Start service
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Creating a New Migration

```bash
# Auto-generate migration from ORM model changes
alembic revision --autogenerate -m "add_new_column_to_table"

# Review the generated file in alembic/versions/
# Verify the upgrade() and downgrade() functions are correct

# Apply
alembic upgrade head

# Verify
alembic current
```

**Always review auto-generated migrations before applying.** Alembic's autogenerate does not detect: column renames (it generates drop + add), computed columns, custom constraints, pgvector index creation, or TSVECTOR trigger creation. These require manual migration steps.

### Rolling Back a Migration

```bash
# Roll back one step
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision_id>

# View migration history
alembic history --verbose
```

**Note:** Rolling back a migration that drops a column causes data loss. Always verify the `downgrade()` function before running in production.

### Adding a New ORM Model

1. Define the SQLAlchemy model class in `app/models/models.py`
2. Define the corresponding Pydantic schemas in `app/models/schemas.py`
3. Create the Alembic migration: `alembic revision --autogenerate -m "add_<model_name>"`
4. Review the generated migration (add indexes, constraints, triggers manually if needed)
5. Apply: `alembic upgrade head`
6. Create the CRUD functions in `app/api/crud.py`
7. Create the router in `app/api/` (follow existing router pattern)
8. Register the router in `app/main.py`
9. Write tests in `tests/`

### First-Time Admin Setup

```bash
cd /home/charlie/Forge/ecosystem/DataForge

# Create admin user interactively
python scripts/create_admin.py

# Or set environment variables for non-interactive:
ADMIN_USERNAME=admin ADMIN_PASSWORD=<strong-password> ADMIN_EMAIL=admin@forge.local \
  python scripts/create_admin.py --non-interactive
```

---

## Deployment Checklist

### Local Development

- [ ] PostgreSQL running on localhost:5432
- [ ] Redis running on localhost:6379
- [ ] `DATABASE_URL` set in `.env`
- [ ] `REDIS_URL` set in `.env`
- [ ] `SECRET_KEY` set to a 32-char hex value
- [ ] `VOYAGE_API_KEY` set
- [ ] `alembic upgrade head` run
- [ ] Admin user created via `scripts/create_admin.py`
- [ ] `GET /health` returns 200

### Docker Compose (Local)

```bash
docker-compose up -d
```

This starts PostgreSQL, Redis, and DataForge. Migrations run automatically via the entrypoint script.

### Production Checklist

- [ ] PostgreSQL primary + at least one replica configured
- [ ] Redis Sentinel configured (3 sentinels minimum)
- [ ] `SECRET_KEY` generated with `secrets.token_hex(32)` and stored in ForgeCommand vault
- [ ] `VOYAGE_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY` in vault
- [ ] `ALLOWED_ORIGINS` lists only production frontend origins (no wildcards)
- [ ] `LOG_LEVEL=INFO` (not DEBUG)
- [ ] nginx or load balancer configured in front of uvicorn
- [ ] Health check endpoint registered with load balancer
- [ ] Prometheus scrape job configured for `/metrics`
- [ ] Grafana dashboards imported
- [ ] Backup schedule confirmed (daily/weekly/monthly + PITR)
- [ ] `alembic upgrade head` run against production DB before traffic cutover
- [ ] Smoke test: `GET /health`, `POST /auth/login`, `POST /api/search`

---

## Common Issues

### `alembic upgrade head` fails with "relation already exists"

The migration was partially applied. Check `alembic_version` table to see current state. If the revision is listed, use `alembic stamp <revision>` to mark it applied without re-running. If not listed, the table was manually created — drop it and re-run.

### Embedding generation fails with "API key invalid"

Check `VOYAGE_API_KEY` in `.env`. Verify with:
```bash
python -c "import voyage; c = voyage.Client(); print(c.embed(['test'], model='voyage-large-2'))"
```

If Voyage is down, set `OPENAI_API_KEY` as fallback. DataForge will automatically use it.

### Search returns no results despite documents existing

1. Check that documents were chunked: `GET /admin/documents/{id}` — verify chunk_count > 0
2. Check pgvector extension: `psql -d dataforge -c "SELECT * FROM pg_extension WHERE extname = 'vector';"`
3. Verify the IVFFlat index exists: `psql -d dataforge -c "\d chunks"`
4. Re-embed a document manually: `POST /admin/documents/{id}` with the same content (triggers re-chunking)

### 409 on finding ingestion (run not finalized)

The run_token's `run_id` claim does not match the path parameter `run_id`. Verify the token was issued for this specific run.

### Redis connection refused

Check Redis is running: `redis-cli ping`. If using Redis Sentinel, verify `REDIS_URL` uses the sentinel URL format, not the node URL.

---

## Performance Tuning

### pgvector Index Tuning

For >100,000 chunks, tune the IVFFlat index:

```sql
-- More lists = slower build, faster query
-- Rule of thumb: lists = sqrt(row_count)
CREATE INDEX CONCURRENTLY ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 300);

-- Tune probes at query time (higher = more accurate, slower)
SET ivfflat.probes = 10;
```

### Connection Pooling

For high-concurrency production deployments, add PgBouncer in front of PostgreSQL:

```
uvicorn (N workers) -> PgBouncer (pool_size=20) -> PostgreSQL
```

Adjust `DATABASE_URL` to point to PgBouncer's port (default: 6432).

### Redis Memory

Monitor Redis memory usage. The cache TTLs in the `/cache` router should be tuned based on actual usage patterns. If Redis memory exceeds 80% of limit, reduce TTLs or increase memory allocation.

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, router registration, lifespan |
| `app/database.py` | SQLAlchemy engine, session factory |
| `app/models/models.py` | All ORM models (31+ classes) |
| `app/models/schemas.py` | All Pydantic schemas (90+) |
| `app/api/crud.py` | Database operations |
| `app/api/search.py` | Hybrid search implementation |
| `app/utils/embeddings.py` | Chunking + embedding generation |
| `app/utils/auth.py` | JWT + bcrypt utilities |
| `alembic/versions/` | Migration history |
| `tests/` | 32 test files |
| `app/models/multi_provider_models.py` | Multi-provider pipeline models (6 tables) |
| `app/models/sentinel_models.py` | Sentinel health + healing models |
| `app/api/sentinel_router.py` | Sentinel sweep + healing REST API |
| `scripts/seed_model_catalog.py` | 14-model catalog seed script |
| `.env.example` | All env vars documented |
| `requirements.txt` | Pinned dependencies |

---

## Version History

| Version | Phases | Status |
|---------|--------|--------|
| v5.3 (current) | 20/20 complete | Multi-provider pipeline + Sentinel agent models |
| v5.2 | 18/18 complete | 296 tests, 82% coverage, 42,732 LOC |
| v5.1 | 17/18 complete | BugCheck integration added |
| v5.0 | 15/18 complete | AuthorForge V2, Teams, Smithy added |
| v4.x | Core platform | NeuroForge, VibeForge, auth, search |

---

*BDS Documentation Protocol v1.0 — Last updated: 2026-02-24*
