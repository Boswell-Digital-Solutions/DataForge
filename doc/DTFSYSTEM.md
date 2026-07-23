# DataForge — Compiled System Reference

**Designation:** DTF
**Document role:** Canonical compiled technical reference for the DataForge durable-truth service
**Source:** `doc/system/`
**Build command:** `bash doc/system/BUILD.sh`
**Document version:** 2.1 (2026-07-23) — FT-02 canonical telemetry event-size parity documented
**Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

> **Generated artifact warning:** `doc/DTFSYSTEM.md` is assembled output. Edit
> the source modules under `doc/system/` and rebuild. Hand edits to the
> compiled artifact are overwritten by the next build.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Primary output: `doc/DTFSYSTEM.md`

This `doc/system/` tree is the canonical source of truth for DataForge. It uses
explicit **truth classes**: *canonical facts* define the source-of-truth
contract, persistence/retrieval authority, write-boundary invariants, fail-closed
posture, and ecosystem contracts; *snapshot facts* are dated, audit-derived
counts (mounted routers, Alembic migrations, Python/test files, collected tests).
See §11 for the scope and authority boundary and §12 for ownership and
designation doctrine. The nested `forge-telemetry/` repo is documented separately.

| Part | File | Contents |
| --- | --- | --- |
| §1 | `00_overview/01-overview-philosophy.md` | Service identity, source-of-truth contract, current role, what it is not |
| §2 | `00_overview/02-architecture.md` | Architecture, persistence + hybrid retrieval, governance surfaces |
| §3 | `00_overview/03-project-structure.md` | Repository tree, module layout |
| §4 | `10_service-contract/04-api-layer.md` | Mounted API families, endpoints, auth |
| §5 | `10_service-contract/05-proving-slice-schema.md` | Proving-slice schema contract |
| §6 | `10_service-contract/06-pressforge-automation-schema.md` | PressForge automation schema contract |
| §7 | `20_runtime/07-backend-internals.md` | CRUD, search, embeddings, lifecycle internals |
| §8 | `20_runtime/08-error-handling.md` | Error handling, lifecycle & access control |
| §9 | `30_dependencies/09-tech-stack.md` | Dependencies, versions, runtime requirements |
| §10 | `30_dependencies/10-ecosystem-integration.md` | Cross-service persistence contracts |
| §11 | `40_governance/11-scope.md` | Service authority boundary, write-boundary, truth classes |
| §12 | `40_governance/12-governance.md` | Ownership, designation doctrine, authority hierarchy |
| §13 | `40_governance/13-change-control.md` | Change classes, evidence, verification commands |
| §14 | `50_operations/14-config-env.md` | Configuration and environment variables |
| §15 | `50_operations/15-testing.md` | Test structure, markers, coverage posture |
| §16 | `50_operations/16-handover.md` | Critical constraints, invariants, migration runbook |
| §17 | `99_appendices/17-appendices.md` | Glossary, cross-references, revision history |

## Quick Assembly

```bash
bash doc/system/BUILD.sh
```

---

# §1 — Overview & Philosophy

## Service Identity

**DataForge** is the resident FastAPI service that owns durable ecosystem truth. It is
the persistence, retrieval, and governance evidence boundary behind the rest of Forge,
not a bootstrap repo or passive library.

- **Runtime posture:** Resident HTTP service
- **Default port:** `8001`
- **Authority boundary:** Postgres-backed durable state, hybrid retrieval, policy/runtime evidence, and scoped write enforcement
- **Mounted router objects:** `46` from `app/main.py` (audit: 2026-07-14)
- **Router modules in source:** `39`
- **Alembic migrations:** `47`
- **Python files under `app/`:** `175`
- **Pytest files:** `39`
- **Collected tests:** `565` via `PYTHONPATH=. ./.venv/bin/pytest --collect-only -q`
- **Nested repo boundary:** `forge-telemetry/` is a separate git repo with its own documentation stack

## The Source-of-Truth Contract

DataForge is not a convenience mirror. Durable state written here is the canonical record
for the ecosystem.

Every major Forge runtime writes authoritative records into DataForge:

- **NeuroForge** persists inference records, model-routing evidence, and learning data.
- **VibeForge** persists projects, sessions, outcomes, analytics, and preferences.
- **AuthorForge** persists project, chapter, scene, manuscript, map, and asset state.
- **ForgeAgents / BugCheck** persist agent definitions, run evidence, findings, enrichments, and lifecycle events.
- **Forge:SMITH** persists planning sessions, deliverables, portfolio projects, and evaluations.
- **ForgeCommand** depends on DataForge for execution evidence, key control, secret sync, and governance-adjacent state.
- **Sentinel / Press / private-source / runtime-governance surfaces** persist sweep records, automation records, profile state, policy envelopes, and promotion receipts.

If a service cannot persist required durable state to DataForge, the operation is not complete.
That fail-closed posture is intentional.

## Current Service Role

### 1. Durable Persistence
PostgreSQL remains the authority boundary for documents, runs, findings, planning state,
authoring assets, pricing data, policy ledgers, press automation records, and private-source
profiles.

### 2. Hybrid Retrieval
DataForge stores chunked documents with vector embeddings and full-text indexes, then
serves semantic, keyword, and fused search through the mounted search routers.

### 3. Scoped Authentication and Write Boundaries
The live mounted surface exposes JWT/token compatibility routes, admin key rotation,
service-key validation, run-scoped write flows, and admin-token protected control surfaces.
The repo also contains a richer secure auth stack in source, but that stack is not mounted
by default and therefore is not part of the live surface contract.

### 4. Runtime Governance Evidence
DataForge now persists policy envelopes, policy ledgers, reward records, runtime-promotion
receipts, candidate approvals/rejections, rate-limit state, and execution evidence for
operator review.

### 5. Platform and Operator Surfaces
The mounted app includes control surfaces for secret sync/read, compression dictionaries,
Sentinel sweep/healing record persistence, PressForge automation tables, FPVS health/version
probes, diligence workflows, and private-source ingestion profiles.

### 6. Fail-Closed Readiness
Redis is derived state only. Database and pgvector readiness drive the authoritative ready
signal. Startup will surface dependency problems through readiness instead of silently
downgrading authority decisions.

## What DataForge Is Not

- **Not a cache authority.** Redis accelerates reads and rate limits; it does not own truth.
- **Not an orchestrator.** ForgeCommand remains the ecosystem operator/control plane.
- **Not an autonomous healer.** Sentinel data is persisted here, but DataForge does not itself perform autonomous repair.
- **Not the live OAuth2/TOTP gateway on the default mounted surface.** Those secure auth modules exist in source only until explicitly wired in `app/main.py`.
- **Not the `forge-telemetry` codebase.** The nested repo is versioned and documented separately.

*See §11 for the invariants that must remain true across future changes.*

---

# §2 — Architecture

## Component Map

```
DataForge (default port 8001)
│
├── FastAPI Application Layer
│   ├── 46 mounted router objects plus app-level health/admin/docs routes
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

# §3 — Project Structure

## Directory Tree

*Last updated: 2026-07-14*

```
DataForge/
├── alembic/                          # Database migration history
│   ├── env.py                        # Alembic environment config (imports ORM models)
│   ├── script.py.mako                # Migration template
│   └── versions/                     # 62 migration version files
│
├── app/                              # Main application package (210 Python files)
│   ├── main.py                       # FastAPI app + lifespan + router registration (46 mounted routers)
│   ├── database.py                   # SQLAlchemy engine, SessionLocal, get_db()
│   ├── config.py                     # Environment config and validation
│   ├── security_config.py            # Security policy helpers
│   ├── logging_config.py             # Structured logging setup
│   │
│   ├── models/                       # ORM models + Pydantic schemas (67 Python files)
│   │   ├── models.py                 # Core: users, documents, chunks, corpus state, execution index, agent registry
│   │   ├── schemas.py                # Core: auth, search, user/domain/document/tag schemas
│   │   ├── agentic_reasoning_models.py / _schemas.py   # Experience store, gate analytics, skill nomination
│   │   ├── agent_registry_schemas.py                   # Agent definition persistence
│   │   ├── authorforge_models.py / _schemas.py         # AuthorForge v1 state
│   │   ├── authorforge_v2_models.py / _schemas.py      # AuthorForge v2 state
│   │   ├── bugcheck_models.py / _schemas.py            # BugCheck runs, findings, enrichments
│   │   ├── buildguard_models.py / _schemas.py          # BuildGuard quality gate records
│   │   ├── compression_models.py / _schemas.py         # Compression dictionary governance
│   │   ├── diligence_models.py / _schemas.py           # Due diligence workflows
│   │   ├── forge_run_schemas.py                        # ForgeRun evidence and index schemas
│   │   ├── multi_provider_models.py / _schemas.py      # Multi-provider routing catalog (6 tables)
│   │   ├── neuroforge_models.py / _schemas.py          # NeuroForge inference + model-routing records
│   │   ├── planning_models.py / _schemas.py            # SMITH multi-AI planning sessions
│   │   ├── policy_envelope_models.py / _schemas.py     # Governed LLM policy envelopes, ledger, bandit state
│   │   ├── press_models.py / _schemas.py               # PressForge campaign + automation state
│   │   ├── private_source_models.py / _schemas.py      # PSIM private source profiles
│   │   ├── proving_slice_models.py / _schemas.py       # Proving-slice intake records + receipts
│   │   ├── rate_limits_models.py / _schemas.py         # Cross-run global rate limit state
│   │   ├── runs_models.py / _schemas.py                # Run evidence blobs and index
│   │   ├── runtime_promotion_models.py / _schemas.py   # Promotion receipts and execution handoff
│   │   ├── runtime_promotion_candidate_models.py / _schemas.py  # Candidate decision records
│   │   ├── sentinel_models.py / _schemas.py            # Sentinel health sweep + healing records
│   │   ├── smithy_planning_models.py / _schemas.py     # Forge:SMITH planning deliverables
│   │   ├── smithy_portfolio_models.py / _schemas.py    # Forge:SMITH portfolio projects
│   │   ├── tarcie_models.py / _schemas.py              # TARCIE event records
│   │   ├── telemetry_models.py / _schemas.py            # Shared events ORM + bounded HTTP ingest
│   │   ├── contracts/
│   │   │   └── telemetry_resource_bounds.v1.json        # Hash-pinned FT-02 authority copy
│   │   ├── team_models.py / _schemas.py                # Team and organization state
│   │   └── vibeforge_models.py / _schemas.py           # VibeForge projects, sessions, analytics
│   │
│   ├── api/                          # API modules (62 Python files; 46 routers mounted in main.py)
│   │   ├── search_router.py          # POST /api/search, GET /api/search/stats
│   │   ├── admin_router.py           # Admin CRUD: documents, domains, tags
│   │   ├── admin_keys_router.py      # Service-key governance
│   │   ├── auth_router.py            # /auth/token + legacy /api/auth routes
│   │   ├── crud.py                   # Core document/domain/tag DB operations
│   │   ├── search.py                 # Hybrid vector + BM25 search logic
│   │   ├── agents_registry_router.py / forge_run_router.py / bugcheck_router.py
│   │   │                             # Agent definitions, run evidence, BugCheck persistence
│   │   ├── runs_router.py / experience_router.py
│   │   │                             # Run history + agentic experience storage
│   │   ├── neuroforge_router.py / neuroforge_crud.py
│   │   │                             # NeuroForge inference record persistence
│   │   ├── multi_provider_router.py / multi_provider_crud.py
│   │   │                             # Provider pricing catalog and batch queue
│   │   ├── projects_router.py / projects_crud.py
│   │   │                             # AuthorForge v1 projects
│   │   ├── authorforge_v2_router.py / authorforge_v2_crud.py
│   │   │                             # AuthorForge v2 state
│   │   ├── smithy_planning_router.py / smithy_planning_crud.py
│   │   ├── smithy_portfolio_router.py / smithy_portfolio_crud.py
│   │   ├── sentinel_router.py        # Sentinel sweep/healing records
│   │   ├── policy_envelope_router.py # Governed LLM policy, ledger, bandit state, rollout labels
│   │   ├── runtime_promotion_router.py / runtime_promotion_candidate_router.py
│   │   │                             # Promotion receipts and candidate decisions
│   │   ├── proving_slice_router.py   # Proving-slice intake + receipt endpoints
│   │   ├── diligence_router.py / diligence_crud.py
│   │   ├── press_router.py           # PressForge automation state
│   │   ├── private_source_router.py / private_source_crud.py
│   │   ├── rate_limits_router.py     # Cross-run global rate limits
│   │   ├── compression_router.py     # Compression dictionary governance
│   │   ├── vibeforge_router.py / learning_router.py
│   │   ├── teams_router.py / tarcie_router.py / secrets_router.py
│   │   ├── telemetry_router.py       # Authenticated generic Forge Telemetry ingest
│   │   ├── fpvs_router.py            # Health/version probe surface
│   │   ├── routes/events_router.py   # Audit event append
│   │   └── (source-present, not mounted: api_deployment_router, auth_revocation_router,
│   │        auth_secure_router, cache_replication_router, dlq_router,
│   │        rate_limit_router, replication_router, tracing_router)
│   │
│   ├── auth/                         # Auth utilities
│   │   ├── api_keys.py               # Service API key validation
│   │   └── token_rotation.py         # JWT rotation helpers
│   │
│   ├── middleware/                   # FastAPI middleware
│   │   ├── correlation.py            # Correlation ID injection
│   │   └── request_timeout.py        # Per-request timeout enforcement
│   │
│   ├── neuroforge/                   # Embedded NeuroForge service helpers
│   │   ├── services/context_builder.py / inference_pipeline.py / post_processor.py / dataforge_client.py
│   │   └── config.py
│   │
│   ├── runtime_promotion/            # Runtime promotion execution handoff
│   │   └── execution_handoff/        # contracts.py, models.py, service.py, status_service.py, worker.py
│   │
│   ├── services/                     # Domain service layer
│   │   ├── embeddings_integration.py
│   │   ├── runs_service.py
│   │   ├── runtime_promotion_candidate_builder.py
│   │   ├── tarcie_service.py
│   │   ├── teams_service.py
│   │   └── vibeforge_service.py
│   │
│   ├── tasks/                        # Background task integration
│   │   └── celery_integration.py
│   │
│   └── utils/                        # Shared utility modules (32 Python files)
│       ├── auth.py                   # JWT creation/validation + bcrypt helpers
│       ├── cache_governance.py       # TTL enforcement, deterministic keys, fail-closed cache helpers
│       ├── corpus_versioning.py      # Atomic corpus version bump + current-version cache
│       ├── embeddings.py             # Text chunking + embedding generation/cache
│       ├── audit_logging.py          # Append-only HMAC-signed audit event writer
│       ├── anomaly_detection.py      # Six auth-layer threat detection patterns
│       ├── rate_limiter.py / rate_limit.py  # Redis sliding-window rate limiter
│       ├── circuit_breaker.py        # Service circuit-breaker pattern
│       ├── data_encryption.py        # AES-256 Fernet field-level encryption
│       ├── redis_utils.py / resilient_embeddings.py / cache_failover.py / cache_replication.py
│       ├── db_failover.py / db_replication.py / load_balancer.py
│       ├── distributed_tracing.py / cross_region_tracing.py
│       ├── metrics.py / compliance_reporting.py / secure_key_storage.py
│       ├── session_manager.py / token_revocation.py / mfa_handler.py / oauth2_oidc.py
│       └── dead_letter_queue.py / task_retry_policy.py / diligence_parser.py
│
├── scripts/
│   ├── create_admin.py               # Interactive CLI: create initial admin user
│   └── seed_model_catalog.py         # Seed canonical model catalog + retire stale xAI aliases
│
├── templates/
│   └── admin.html                    # Self-contained Jinja2 admin UI template
│
├── static/                           # Static assets (CSS, JS) for admin UI
│
├── tests/                            # 54 test files, 730 collected tests as of 2026-07-14
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
│   └── ... (54 test files total)
│
├── forge-telemetry/                  # Nested git repo; shared telemetry library with its own docs stack
│   ├── doc/system/                   # Separate library system docs
│   ├── forge_telemetry/              # Published package surface
│   ├── scripts/context-bundle.sh     # Selective context loader for the nested repo
│   └── CLAUDE.md                     # Nested repo working instructions
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
The FastAPI application entry point. Defines the `lifespan` context manager (configuration validation, pgvector init, shutdown cleanup). Registers the 46 currently mounted router objects, configures CORS and request-timeout middleware, mounts `static/` when present, and registers exception handlers.

**Critical:** The order of router registration matters. Auth routes must be registered before protected routes. The health endpoint (`/health`) must be registered without auth middleware. Router modules that exist in `app/api/` but are not included here are source-present only and should not be documented as live API surface.

### `app/database.py`
Creates the SQLAlchemy `engine` from `DATAFORGE_DATABASE_URL`. Provides `SessionLocal` for synchronous sessions and `get_db()` as a FastAPI dependency. The engine applies connect, pool, statement, lock, and idle-in-transaction timeouts. pgvector extension initialization is handled during startup in `app/main.py`, not in `database.py`.

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `app/models/models.py`
Contains the core shared ORM tables that anchor the service:

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | Auth identity and admin status |
| `Domain` | `domains` | Knowledge organization hierarchy |
| `Tag` | `tags` | Document labels |
| `Document` | `documents` | Canonical stored documents and metadata |
| `Chunk` | `chunks` | Text chunks, embeddings, and search indexes |
| `CorpusState` | `corpus_state` | Single-row current retrieval corpus version |
| `CorpusVersion` | `corpus_versions` | Append-only corpus version history |
| `ExecutionIndex` | `execution_index` | Fast run lookup/status surface |
| `RunEvidence` | `run_evidence` | Full JSON evidence blobs |
| `AgentRegistry` | `agent_registry` | Agent definition persistence |

Most domain tables no longer live in `models.py`. Authoring, BugCheck, policy envelopes,
press automation, runtime promotion, rate limits, Sentinel, SMITH, teams, and provider
catalog state are defined in companion `*_models.py` modules under `app/models/`.

### `app/models/schemas.py`
Contains the core shared Pydantic schemas for users, auth tokens, domains, tags, documents,
chunks, and search. Domain-specific request/response contracts live in companion
`*_schemas.py` modules alongside their model families.

### `app/api/crud.py`
Document/domain/tag CRUD plus document-processing orchestration. Document writes perform
chunking, embedding generation, document-cache invalidation, and corpus version bumps for
insert, reindex, and delete flows.

### `app/api/search.py`
Implements `hybrid_search()`. Runs vector similarity query (pgvector `<=>` cosine operator) and BM25 full-text query in parallel, then merges via RRF. Returns ranked list of chunks with parent document metadata.

### `app/utils/cache_governance.py`
Shared cache policy helpers: deterministic retrieval/doc/embed keys, TTL-required Redis
writes, cache invalidation logging, and fail-closed authority fallbacks.

### `app/utils/corpus_versioning.py`
Implements the atomic `UPDATE ... RETURNING` corpus bump, append-only audit insert, and
short-lived caching of `corpus_version:current`.

### `app/utils/embeddings.py`
`chunk_text(text, chunk_size, overlap)` — token-aware splitter.
`generate_embedding(text)` / batch helpers — NeuroForge-first embedding flow plus
Redis-backed derived caching.

### `alembic/versions/`
62 migration files covering the base schema plus later domain additions, pgvector support,
pipeline tables, Sentinel tables, private source profiles, and corpus-governance state.
Always run `alembic upgrade head` after pulling new code.

---

# §4 — API Layer

*Last updated: 2026-07-14*

The live API contract is whatever `app.main:app` mounts. A route audit against `app.routes`
on 2026-07-14 confirmed `46` mounted router objects plus app-level docs, HTML views, and
probe routes. `app/api/` contains additional routers, but they are not part of the live
surface until explicitly included in `app/main.py`.

This service exposes both JSON APIs and a small HTML surface. It is incorrect to treat the
entire mounted surface as JSON-only.

## Canonical Probe and HTML Routes

| Surface | Paths | Notes |
|---------|-------|-------|
| Root info | `/` | Basic service entrypoint |
| Health | `/health`, `/health/render` | Liveness and rendered health surface |
| Readiness | `/ready` | Dependency-aware readiness |
| Version | `/version` | FPVS version/build metadata |
| Admin HTML | `/admin`, `/admin-ui` | Server-rendered operator view |
| Diligence HTML | `/diligence`, `/diligence/dashboard`, `/diligence/new`, `/diligence/projects/{project_id}`, `/diligence/reviews/{review_id}` | Server-rendered diligence views |
| OpenAPI docs | `/docs`, `/redoc`, `/openapi.json` | Development/operator documentation |

There is **no root `/metrics` route mounted by default** in the current app.

## Mounted Router Families

| Family | Key prefixes | Representative mounted routes | Notes |
|--------|--------------|-------------------------------|-------|
| Search and document admin | `/api/search`, `/admin/documents`, `/admin/domains`, `/admin/tags` | `POST /api/search`, `POST /api/search/hybrid`, `GET /api/search/stats`, `POST /admin/documents` | Hybrid retrieval plus document/domain/tag CRUD |
| Auth compatibility and operator key control | `/auth`, `/api/auth`, `/auth/whoami`, `/admin/api-keys`, `/admin/token` | `POST /auth/token`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /admin/api-keys/generate`, `POST /admin/token/rotate` | Live mounted auth is JWT/login compatibility plus admin key/token tooling |
| NeuroForge and learning | `/api/neuroforge`, `/api/v1/runs`, `/api/v1/learning` | `POST /api/neuroforge/inferences`, `POST /api/neuroforge/routing-decisions`, `POST /api/v1/runs`, `GET /api/v1/learning/model-performance` | Inference, routing, run logging, and learning feedback |
| VibeForge and team state | `/api/vibeforge`, `/api/teams` | `POST /api/vibeforge/projects`, `POST /api/vibeforge/sessions`, `GET /api/teams/{team_id}`, `GET /api/teams/{team_id}/insights` | Project/session persistence and team insights |
| AuthorForge content graph | `/api/projects` | `POST /api/projects`, `POST /api/projects/{project_id}/chapters`, `POST /api/projects/manuscripts`, `GET /api/projects/{project_id}/map/settings` | Large mounted authoring/content surface with chapters, scenes, maps, assets, collections, arcs, and alerts |
| Forge:SMITH | `/api/v1/smithy/planning`, `/api/v1/smithy/portfolio` | `POST /api/v1/smithy/planning/sessions`, `POST /api/v1/smithy/planning/sessions/{session_id}/start`, `POST /api/v1/smithy/portfolio/projects` | Planning session state, deliverables, and portfolio/evaluation records |
| Agents, runs, and BugCheck | `/api/v1/agents`, `/api/v1/forge-run`, `/api/v1/bugcheck`, `/api/v1/experience` | `POST /api/v1/agents`, `POST /api/v1/forge-run/persist`, `POST /api/v1/bugcheck/runs/{run_id}/findings`, `POST /api/v1/experience` | Agent registry, execution evidence, BugCheck persistence, experience store |
| Governance and runtime shaping | `/api/v1/runtime-promotion`, `/api/v1/policy-envelopes`, `/api/v1/policy-runs`, `/api/v1/policy-routing` | `POST /api/v1/runtime-promotion/receipts/local-failure-pattern`, `POST /api/v1/runtime-promotion/candidates/{candidate_id}/approve`, `PUT /api/v1/policy-envelopes/{policy_key}`, `POST /api/v1/policy-runs/ledger` | Promotion receipts, candidate review, deterministic policy envelopes, bandit state, reward records |
| Diligence and event persistence | `/api/diligence`, `/api/v1/events`, `/api/v1/telemetry`, `/ingest/tarcie` | `POST /api/diligence/reviews`, `POST /api/diligence/findings`, `POST /api/v1/events`, `POST /api/v1/telemetry/events:batch`, `POST /ingest/tarcie` | Compliance review workflows, BuildGuard event ingest, authenticated bounded generic Forge Telemetry ingest, Tarcie friction ingest |
| Platform and operator data surfaces | `/secrets`, `/api/v1/models`, `/api/v1/pricing`, `/api/v1/costs`, `/api/v1/batch`, `/api/v1/rate-limits`, `/api/v1/sentinel`, `/api/compression/dictionaries`, `/api/v1/press`, `/api/v1/private-source-profiles` | `POST /secrets/sync`, `POST /api/v1/rate-limits/check`, `POST /api/v1/sentinel/sweeps`, `POST /api/compression/dictionaries`, `POST /api/v1/private-source-profiles`, `POST /api/v1/press/automation/runs` | Secrets relay, catalog/pricing/costs, rate-limit governance, Sentinel persistence, compression dictionaries, private-source profiles, and PressForge automation |
| Proving-slice intake | `/api/v1/proving-slice` | `POST /api/v1/proving-slice/intake`, `GET /api/v1/proving-slice/receipts/by-artifact/{artifact_id}` | Governed artifact intake from DataForge Local: validate via forge-contract-core, persist, emit promotion_receipt. Three intake outcomes: `accepted`, `rejected`, `duplicate_reconciled`. |

## Authentication Posture

Credential requirements vary by router. The live mounted service currently uses these categories:

- `POST /api/v1/telemetry/events:batch` requires a durable DataForge service key. Keys with
  `service` or `scopes` metadata are constrained to that service and must include
  `telemetry:write`; legacy unscoped service keys remain accepted during migration. The endpoint
  accepts at most 100 Forge Telemetry v0.3 events and 256 KiB per batch, then writes
  idempotently by `event_id`. Each complete event is RFC 8785-canonicalized and must
  fit the authority-pinned 65,536-byte ceiling. The limit is not applied separately
  to `metadata` and `metrics`; an oversized event fails validation with the stable
  `event_size_exceeded` code.

| Credential type | Examples |
|-----------------|----------|
| No auth | `/`, `/docs`, `/redoc`, `/openapi.json`, `/health`, `/health/render`, `/ready`, `/version`, HTML dashboards |
| Form or JSON login payload | `/auth/token`, `/api/auth/login`, `/api/auth/register` |
| JWT bearer | `/api/auth/me` and many user-facing CRUD surfaces |
| Admin token / emergency key / admin headers | `/admin/api-keys/*`, `/admin/token/*`, `/secrets/*` |
| Service API keys / scoped run credentials | BugCheck, event, policy, promotion, pricing, rate-limit, and integration surfaces as enforced by their handlers |

The repo contains a richer secure auth stack in `auth_secure_router.py`, but that router is
not mounted and therefore is not part of the live contract.

## Source-Present but Not Mounted by Default

These routers exist in `app/api/`, but the route audit confirmed they are absent from the
live app surface:

| Router module | Intended surface |
|---------------|------------------|
| `api_deployment_router` | deployment/load-balancer control |
| `auth_revocation_router` | token revocation and metrics |
| `auth_secure_router` | OAuth2/OIDC, MFA, and secure auth flows |
| `cache_replication_router` | cache failover and replication |
| `dlq_router` | dead-letter queue management |
| `rate_limit_router` | alternate/internal rate-limit management surface |
| `replication_router` | database replication/failover control |
| `tracing_router` | tracing and metrics ingestion/query |

## Contract Invariants

- Do not document a router as live unless it appears in `app.main`.
- Do not document `/metrics` as a supported root route until a mounted route actually exposes it.
- Preserve the distinction between HTML operator pages and JSON APIs.
- Keep prefixes exact: the current live service uses both legacy `/api/auth` style routes and newer `/api/v1/*` families.

---

# §5 — Proving-Slice Schema

*Last updated: 2026-04-04*

Added in migration `20260404_10` (down_revision: `20260401_02`).

Two tables in the default public schema.

## ps_cloud_intake_records

Durable intake log. One row per artifact received from DataForge Local. The `idempotency_key`
UNIQUE constraint is the duplicate-detection boundary: a second submission with the same
key is reconciled without re-running validation.

| Column | Type | Notes |
|--------|------|-------|
| `intake_id` | VARCHAR(36) PK | UUID assigned at intake |
| `artifact_id` | VARCHAR(36) NOT NULL | From the incoming shared envelope |
| `artifact_family` | VARCHAR(128) NOT NULL | `source_drift_finding` or `promotion_envelope` |
| `artifact_version` | INTEGER NOT NULL | Schema version |
| `idempotency_key` | VARCHAR(64) NOT NULL UNIQUE | 64-char hex sha256; duplicate detection key |
| `produced_by_system` | VARCHAR(255) NOT NULL | Originating system (e.g. `dataforge-Local`) |
| `lineage_root_id` | VARCHAR(36) NOT NULL | Root of the artifact lineage chain |
| `trace_id` | VARCHAR(128) NOT NULL | Distributed trace identifier |
| `intake_outcome` | VARCHAR(64) NOT NULL | `accepted` / `rejected` / `duplicate_reconciled` |
| `rejection_class` | TEXT | Populated when `intake_outcome = rejected` |
| `rejection_detail` | TEXT | Human-readable rejection explanation |
| `shared_record_ref` | TEXT | Canonical `<family>:<id>:v<n>:shared` ref; set on acceptance |
| `payload_json` | JSONB NOT NULL | Family-specific payload from the artifact |
| `envelope_json` | JSONB NOT NULL | All envelope fields except `payload` |
| `received_at` | TIMESTAMPTZ NOT NULL | When the intake request was received |
| `processed_at` | TIMESTAMPTZ NOT NULL | When validation and persistence completed |

**Indexes:** `artifact_id`, `artifact_family`, `intake_outcome`, `received_at`, `lineage_root_id`

## ps_cloud_receipts

One row per receipt artifact emitted back to DataForge Local. Each `ps_cloud_intake_records`
row produces exactly one receipt row. The `receipt_artifact_id` is the `artifact_id` carried
by the `promotion_receipt` artifact returned to the caller.

| Column | Type | Notes |
|--------|------|-------|
| `receipt_id` | VARCHAR(36) PK | UUID |
| `intake_id` | VARCHAR(36) NOT NULL FK → ps_cloud_intake_records | |
| `artifact_id` | VARCHAR(36) NOT NULL | From the submitted artifact |
| `receipt_artifact_id` | VARCHAR(36) NOT NULL UNIQUE | `artifact_id` of the emitted promotion_receipt |
| `intake_outcome` | VARCHAR(64) NOT NULL | Mirrors `ps_cloud_intake_records.intake_outcome` |
| `rejection_class` | TEXT | Populated when rejected |
| `retry_allowed` | BOOLEAN NOT NULL DEFAULT FALSE | Always false for contract validation rejections |
| `outcome_summary` | TEXT | Human-readable explanation |
| `shared_record_ref` | TEXT | Canonical shared record reference |
| `emitted_at` | TIMESTAMPTZ NOT NULL | When the receipt was emitted |

**Indexes:** `artifact_id`, `intake_id`, `intake_outcome`

## Intake Decision Logic

```
POST /api/v1/proving-slice/intake

1. Family gate: only source_drift_finding and promotion_envelope admitted → 422 otherwise
2. Duplicate check: lookup idempotency_key in ps_cloud_intake_records
   → if found: return duplicate_reconciled receipt (original shared_record_ref preserved)
3. validate_artifact(artifact, strict_idempotency=True) via forge-contract-core
   → if ArtifactValidationError: persist rejected row + emit rejected receipt
4. Persist ps_cloud_intake_records (accepted) + ps_cloud_receipts
5. Return ProofReceiptArtifact (promotion_receipt family, intake_outcome=accepted)
```

The HTTP status is always `200` for domain decisions (accepted / rejected / duplicate).
`422` is reserved for unsupported families — a caller error, not a domain rejection.

## Receipt Artifact Structure

The returned receipt is a complete, schema-conforming `promotion_receipt` artifact:

- `artifact_family`: `promotion_receipt`
- `produced_by_system`: `DataForge`
- `signer_identity`: `DataForge/proving_slice_intake@proving-slice-v1`
- `payload.intake_outcome`: `accepted` | `rejected` | `duplicate_reconciled`
- `payload.shared_record_ref`: set when `accepted` or `duplicate_reconciled`
- `payload.rejection_class`: set when `rejected`
- `payload.retry_allowed`: always `false` for contract validation failures

Signature is a placeholder (`sha256:cloud-proving-slice-v1-{hash}`) — cryptographic
signing is deferred to Stage 5 key governance.

## GET /api/v1/proving-slice/receipts/by-artifact/{artifact_id}

Returns the receipt for a previously submitted artifact. DataForge Local uses this endpoint
to reconcile ambiguous sends — when the original `POST /intake` response was lost in transit,
Local can re-query by `artifact_id` to determine the true intake outcome.

Returns `404` if the `artifact_id` has never been processed.

## Test Coverage

`tests/test_proving_slice_intake.py` — **29 tests, no live PostgreSQL required** (SQLite in-memory via `tests/conftest.py`).

*Last updated: 2026-04-04*

| Class | Tests | What is verified |
|-------|-------|-----------------|
| `TestIntakeAccepted` | 8 | 200 response; receipt family/version; `accepted` outcome; shared_record_ref; `produced_by_system=DataForge`; intake + receipt rows written to DB |
| `TestIntakeDuplicate` | 3 | `duplicate_reconciled` on second submit; exactly one intake row; shared_record_ref preserved from original |
| `TestIntakeRejected` | 5 | `rejected` outcome; rejection_class present; `retry_allowed=false`; rejected row persisted; end-to-end malformed artifact without patching |
| `TestIntakeFamilyGate` | 3 | `promotion_receipt` → 422; unknown family → 422; `promotion_envelope` admitted |
| `TestReceiptLookup` | 4 | 200 after intake; artifact_id echoed; receipt family; 404 for unknown artifact_id |
| `TestIntakeAdversarial` | 6 | Replay with swapped artifact_id; tampered lineage_root_id; conflicting idempotency key; unknown producer; oversize payload; receipt-family 422 |

Adversarial tests do **not** patch `validate_artifact` — they verify the real contract-core validation pipeline fires and produces `rejected` outcomes for malformed submissions.

---

# §6 — PressForge Automation Schema

## 12. PressForge Automation Schema

> 11 new `pf_*` tables and column additions supporting the PressForge automation loop: governed job execution, GEO visibility tracking, social draftsets, prompt packs, agentic governance, config-as-code, and campaign outcomes.

### Overview

PressForge automation adds 11 tables to DataForge's existing 10 `pf_*` tables (journalists, campaigns, matches, pitches, outreach events, coverage, domain reputation, AI audit log, evidence items, retrieval runs). These support the NeuroForge automation runner's 9 tiered jobs.

All automation state persists here. NeuroForge is stateless beyond a run.

### New Tables (11)

#### `pf_automation_jobs` — Job Definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Job definition ID |
| `job_key` | String(100) | NOT NULL, UNIQUE | e.g. `journalist_refresh`, `disinfo_scan` |
| `description` | Text | nullable | Human-readable job description |
| `cron_schedule` | String(100) | NOT NULL | Cron expression, e.g. `0 3 * * *` |
| `config` | JSONB | NOT NULL, default {} | Job-specific configuration |
| `enabled` | Boolean | NOT NULL, default true | Whether job should run |
| `tier` | Integer | NOT NULL, CHECK 1–4 | Job tier classification |
| `cost_class` | String(20) | NOT NULL, default "low" | CHECK: low, medium, high |
| `last_run_at` | DateTime | nullable | Last successful execution |
| `created_at` | DateTime | NOT NULL | Record creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification timestamp |

**Relationships:** `runs → PfAutomationRun[]` (cascade delete)

#### `pf_automation_runs` — Execution Log

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Run instance ID |
| `job_id` | UUID | FK → pf_automation_jobs, CASCADE | Parent job |
| `job_key` | String(100) | NOT NULL, indexed | Denormalized for fast queries |
| `status` | String(20) | NOT NULL, CHECK | queued, running, success, failed, skipped |
| `started_at` | DateTime | nullable | Execution start |
| `ended_at` | DateTime | nullable | Execution end |
| `attempt` | Integer | NOT NULL, default 1 | Retry attempt number |
| `inputs_hash` | String(128) | nullable | Deterministic hash of inputs |
| `summary` | JSONB | nullable | Job-specific result summary |
| `error` | Text | nullable | Error message on failure |
| `cost_tokens` | Integer | nullable | Total LLM tokens consumed |
| `batch_id` | String(200) | nullable | Provider batch job ID |
| `provider_used` | String(50) | nullable | Which provider handled this run |
| `provider_latency_ms` | Integer | nullable | Provider response latency |
| `created_at` | DateTime | NOT NULL | Record creation timestamp |

**Relationships:** `job → PfAutomationJob`, `alerts → PfAutomationAlert[]`, `agent_logs → PfAgentLog[]`

#### `pf_automation_alerts` — Operator Alerts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Alert ID |
| `run_id` | UUID | FK → pf_automation_runs, SET NULL | Originating run |
| `job_key` | String(100) | NOT NULL, indexed | Source job |
| `severity` | String(10) | NOT NULL, CHECK | info, warn, high |
| `title` | String(300) | NOT NULL | Alert headline |
| `detail` | Text | nullable | Extended description |
| `context` | JSONB | NOT NULL, default {} | Structured alert data |
| `dismissed` | Boolean | NOT NULL, default false | Operator acknowledged |
| `dismissed_by` | String(100) | nullable | Who dismissed |
| `dismissed_at` | DateTime | nullable | When dismissed |
| `created_at` | DateTime | NOT NULL | Alert timestamp |

#### `pf_automation_overrides` — Runtime Config Overrides

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Override ID |
| `job_key` | String(100) | NOT NULL, indexed | Target job |
| `override_config` | JSONB | NOT NULL | Merged over YAML baseline |
| `reason` | Text | NOT NULL | Governance audit trail |
| `expires_at` | DateTime | NOT NULL | Max 7 days from creation |
| `created_by` | String(100) | NOT NULL | Source identifier |
| `created_at` | DateTime | NOT NULL | Override creation timestamp |

#### `pf_agent_logs` — Agentic Governance Audit (Append-Only)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Log entry ID |
| `run_id` | UUID | FK → pf_automation_runs, SET NULL | Associated run |
| `job_key` | String(100) | NOT NULL, indexed | Source job |
| `action_type` | String(100) | NOT NULL, CHECK | Decision type (see below) |
| `input_state` | JSONB | NOT NULL, default {} | State before decision |
| `decision_rationale` | Text | NOT NULL | Why this decision was made |
| `output_action` | JSONB | NOT NULL, default {} | Action taken |
| `risk_flags` | JSONB | NOT NULL, default {} | Risk assessment metadata |
| `accepted` | Boolean | nullable | null until human responds |
| `accepted_by` | String(100) | nullable | Human reviewer |
| `created_at` | DateTime | NOT NULL | Decision timestamp |

**Action types (CHECK):** `route_priority`, `suggest_config`, `widen_query`, `escalate_human`, `auto_pause`, `reactive_trigger`, `self_heal`

**Governance:** No UPDATE or DELETE endpoints. Append-only by design.

#### `pf_provider_configs` — Multi-Provider Routing

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Config ID |
| `provider_key` | String(50) | NOT NULL, UNIQUE | e.g. anthropic, openai, xai |
| `display_name` | String(100) | NOT NULL | Human-readable name |
| `api_base_url` | String(500) | nullable | Provider API endpoint |
| `supports_batch` | Boolean | NOT NULL, default false | Batch API support |
| `cost_per_1m_input` | Float | nullable | Cost per 1M input tokens |
| `cost_per_1m_output` | Float | nullable | Cost per 1M output tokens |
| `max_context_window` | Integer | nullable | Max context size |
| `circuit_breaker_status` | String(20) | NOT NULL, CHECK | closed, open, half_open |
| `rate_limit_rpm` | Integer | nullable | Rate limit (requests/min) |
| `config` | JSONB | NOT NULL, default {} | Provider-specific settings |
| `enabled` | Boolean | NOT NULL, default true | Provider active |

#### `pf_geo_probes` — GEO Visibility Probe Results

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Probe ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Target campaign |
| `provider` | String(50) | NOT NULL | chatgpt, claude, gemini, perplexity |
| `template_id` | UUID | FK → pf_geo_probe_templates, SET NULL | Source template |
| `prompt_text` | Text | NOT NULL | Query sent to provider |
| `response_excerpt` | Text | nullable | Truncated response |
| `brand_mentioned` | Boolean | NOT NULL, default false | Was entity found? |
| `citation_found` | Boolean | NOT NULL, default false | Was citation present? |
| `sentiment` | String(20) | nullable, CHECK | positive, neutral, negative |
| `competitor_mentions` | JSONB | NOT NULL, default [] | Competitor presence |
| `latency_ms` | Integer | nullable | Response latency |
| `probed_at` | DateTime | NOT NULL | When probe was executed |

#### `pf_geo_probe_templates` — GEO Probe Templates

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Template ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `prompt_text` | Text | NOT NULL | Probe question template |
| `intent_category` | String(100) | nullable | discovery, comparison, recommendation |
| `funnel_stage` | String(50) | nullable | awareness, consideration, decision |
| `auto_generated` | Boolean | NOT NULL, default false | Was template auto-created |

#### `pf_social_draftsets` — Social Media Draft Sets

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Draftset ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `bundle_hash` | String(71) | nullable | EAE evidence bundle hash |
| `intent` | String(50) | nullable | announce, insight, proof, bts |
| `platforms` | JSONB | NOT NULL, default [] | Target platforms |
| `drafts` | JSONB | NOT NULL, default [] | Per-platform drafts |
| `schema_json_ld` | JSONB | nullable | JSON-LD structured data |
| `coverage_warnings` | JSONB | NOT NULL, default [] | EAE coverage warnings |
| `status` | String(20) | NOT NULL, CHECK | draft, reviewed, approved |

#### `pf_prompt_packs` — AI Image Prompt Packs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Pack ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `pack_name` | String(200) | nullable | Display name |
| `sora_prompt` | Text | nullable | Sora (16:9) prompt |
| `chatgpt_image_prompt` | Text | nullable | DALL-E 3 (1:1) prompt |
| `gemini_prompt` | Text | nullable | Imagen 3 (4:3) prompt |
| `negative_constraints` | Text | nullable | What to avoid |
| `aspect_ratios` | JSONB | NOT NULL, default {} | Per-platform sizing |
| `alt_text` | Text | nullable | Accessibility text |
| `status` | String(20) | NOT NULL, CHECK | draft, reviewed, approved |

#### `pf_campaign_outcomes` — Campaign Outcome Signals

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Outcome ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `bundle_hash` | String(71) | nullable | Associated EAE bundle |
| `outcome_type` | String(50) | NOT NULL, CHECK | See below |
| `outcome_weight` | Integer | NOT NULL | Signal weight |
| `journalist_id` | UUID | FK → pf_journalists, SET NULL | Associated journalist |
| `notes` | Text | nullable | Free-text notes |
| `context` | JSONB | NOT NULL, default {} | Structured metadata |
| `discovered_at` | DateTime | NOT NULL | When outcome was observed |

**Outcome types (CHECK):** `coverage_secured`, `followup_requested`, `reply_received`, `open_confirmed`, `bounce`, `anti_ai_flagged`

### Column Additions to Existing Tables

#### `pf_campaigns` — New Columns

| Column | Type | Description |
|--------|------|-------------|
| `campaign_type` | String(50) | media, social, geo, mixed |
| `geo_share_pre` | Float | Baseline GEO share before campaign |
| `geo_share_post` | Float | GEO share after automation (updated by geo_share_tracker) |
| `cost_per_cycle` | Float | Average cost per automation cycle |

#### `pf_evidence_items` — New Columns

| Column | Type | Description |
|--------|------|-------------|
| `ai_stance` | String(50) | supportive, neutral, hostile, unknown |
| `disclosure_policy` | Text | Publisher's AI disclosure policy text |

### CRUD Endpoints

All 11 tables follow the standard DataForge CRUD pattern with pagination, filtering, and proper FK cascade handling.

| Table | Endpoints | Notes |
|-------|-----------|-------|
| `pf_automation_jobs` | GET (list), GET/{id}, POST, PATCH/{id} | Job definition management |
| `pf_automation_runs` | GET (list), GET/{id}, POST, PATCH/{id} | Run lifecycle tracking |
| `pf_automation_alerts` | GET (list), GET/{id}, POST, PATCH/{id} | Alert creation + dismiss |
| `pf_automation_overrides` | GET (list), POST | Override creation (TTL-enforced) |
| `pf_agent_logs` | GET (list), GET/{id}, POST | **Append-only — no PATCH/DELETE** |
| `pf_provider_configs` | GET (list), GET/{id}, POST, PATCH/{id} | Provider routing metadata |
| `pf_geo_probes` | GET (list), GET/{id}, POST | Probe result storage |
| `pf_geo_probe_templates` | GET (list), GET/{id}, POST, PATCH/{id}, DELETE/{id} | Template CRUD |
| `pf_social_draftsets` | GET (list), GET/{id}, POST, PATCH/{id} | Draftset lifecycle |
| `pf_prompt_packs` | GET (list), GET/{id}, POST, PATCH/{id} | Prompt pack management |
| `pf_campaign_outcomes` | GET (list), GET/{id}, POST | Outcome signal recording |

### Indexes

| Table | Column(s) | Type | Purpose |
|-------|-----------|------|---------|
| `pf_automation_runs` | `job_id` | btree | FK join performance |
| `pf_automation_runs` | `job_key` | btree | Status queries |
| `pf_automation_alerts` | `run_id` | btree | Run → alerts lookup |
| `pf_automation_alerts` | `job_key` | btree | Job-level alert queries |
| `pf_agent_logs` | `run_id` | btree | Run → log lookup |
| `pf_agent_logs` | `job_key` | btree | Job-level audit queries |
| `pf_automation_overrides` | `job_key` | btree | Override resolution |
| `pf_geo_probes` | `campaign_id` | btree | Campaign probe history |
| `pf_geo_probe_templates` | `campaign_id` | btree | Template lookup |
| `pf_social_draftsets` | `campaign_id` | btree | Campaign draftsets |
| `pf_prompt_packs` | `campaign_id` | btree | Campaign prompt packs |
| `pf_campaign_outcomes` | `campaign_id` | btree | Campaign outcomes |
| `pf_provider_configs` | `provider_key` | unique | Provider lookup |

### Migrations

| Migration | Description |
|-----------|-------------|
| `20260226_0100_pressforge_automation_tables` | Creates 11 new tables with FK relationships |
| `20260226_0200_pressforge_column_additions` | ALTER TABLE additions to `pf_campaigns` and `pf_evidence_items` |

**Dependency:** Both migrations depend on the existing PressForge Phase 2 migration chain (`pressforge_phase2_001` → `pressforge_v12_001` → `pressforge_v12_002`).

### Governance Invariants

1. **`pf_agent_logs` is append-only** — No UPDATE or DELETE at API level
2. **Override TTL enforced** — `expires_at` max 7 days from `created_at`
3. **All automation state in DataForge** — NeuroForge runner is stateless
4. **FK CASCADE on delete** — Deleting a campaign cascades to probes, draftsets, outcomes, templates
5. **FK SET NULL on soft references** — Deleting a run leaves alerts and agent logs intact

### Table Count

After these additions, PressForge uses **21 `pf_*` tables** total:
- Original 10: journalists, campaigns, matches, pitches, outreach_events, coverage, domain_reputation, ai_audit_log, evidence_items, retrieval_runs
- New 11: automation_jobs, automation_runs, automation_alerts, automation_overrides, agent_logs, provider_configs, geo_probes, geo_probe_templates, social_draftsets, prompt_packs, campaign_outcomes

*Added: 2026-02-25*

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

Embeddings are generated during document processing and cached as derived Redis state using
hash-addressed keys (`embed:{model}:{text_hash}`) with an explicit TTL. The preferred runtime
path is NeuroForge-first, with direct provider fallbacks retained for compatibility.

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

**Key rotation:** Requires an explicit migration or dedicated rotation utility to re-encrypt
existing records with the new key. Do not assume a checked-in helper script exists unless it
is present in the repo at the time of the change.

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

Each detection type runs as an async check after the primary auth validation succeeds. Detection results are written to the audit log via `POST /api/v1/events`. The auth response is returned to the caller only after all anomaly checks complete (detections are non-blocking for legitimate users; blocking only on hard violations like brute force).

---

## Memory Governance

DataForge now enforces a hard cache-governance boundary:

1. Postgres/Supabase is authoritative
2. Redis is derived and disposable
3. Redis writes require TTL at write time
4. Cache keys must be deterministic and version-aware
5. Redis failures must never widen access

### Shared Helpers

`app/utils/cache_governance.py` provides:

- `redis_set_with_ttl()` / `redis_set_with_ttl_sync()` for TTL enforcement
- `canonicalize_query()` for order-insensitive query normalization
- `build_retrieval_cache_key()` for version-aware retrieval keys
- `require_authoritative_source()` helpers for fail-closed authority reads
- cache invalidation helpers that log every explicit invalidation

### Corpus Versioning

`app/utils/corpus_versioning.py` maintains monotonic corpus freshness:

- `corpus_state.current_version` is bumped atomically
- `corpus_versions` records the triggering event (`doc_insert`, `chunk_insert`, `reindex`, `doc_delete`, `initial`)
- `corpus_version:current` is cached for 60 seconds and deleted on every bump

Because retrieval keys include corpus version, version bumps invalidate old retrieval caches
without needing a mass delete.

## Rate Limiting

DataForge uses a Redis-backed sliding-window limiter for distributed enforcement.

```
Per request:
  1. Remove timestamps older than the active window
  2. Count remaining requests in the Redis sorted set
  3. If count >= limit: return 429
  4. Add the current request timestamp
  5. Set TTL to window_length + 60 seconds
```

On Redis outage, the limiter fails closed and denies the request. This is intentional: a cache
or Redis failure must never expand access.

---

## Governed LLM Policy Persistence

`app/api/policy_envelope_router.py` backs the Slice 1 and Slice 2 governance records used by
ForgeAgents:

- policy envelopes
- per-call ledger entries
- run finalization records
- bandit state partitions
- reward records and atomic outcome writes

Slice 4 rollout labeling is persisted in ledger/reward payload schemas as optional strict fields:
- `policy_mode_used`
- `policy_id_used`
- `baseline_policy_id`
- `is_canary`
- rollout reason and shadow-evaluation metadata fields

These routes intentionally use synchronous FastAPI handlers because the implementation is built
on the synchronous SQLAlchemy session from `app/database.py`. Keeping the handler itself sync
pushes the ORM work into FastAPI's threadpool, which prevents long-running governance reads or
writes from blocking the event loop and starving `/health`.

This matters most for `GET /api/v1/policy-routing/bandit-states/...` and
`POST /api/v1/policy-runs/finalize`, because ForgeAgents calls them inline during governed
execution and shutdown of policy runs.

---

## Startup Dependency Handling

`app/main.py` performs a best-effort `CREATE EXTENSION IF NOT EXISTS vector` during startup.
That step is advisory, not a boot gate. If Supabase/Postgres is temporarily unavailable, the
process now continues to start, exposes `/health`, and leaves `/ready` to report the database
or pgvector failure until connectivity recovers.

`DATAFORGE_SKIP_STARTUP_DB_INIT=1` remains available for tests and controlled operational
workarounds when startup DB initialization should be bypassed entirely.

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

**The audit log table has no UPDATE or DELETE operations in the ORM.** The only permitted operation is INSERT. The `/api/v1/events` router has no PATCH or DELETE endpoints.

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

# §8 — Error Handling, Lifecycle & Access Control

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
| `NEW → APPROVED` | 409 — must pass through TRIAGED |
| `NEW → APPLIED` | 409 — multiple steps skipped |
| `VERIFIED → NEW` | 409 — backward transition |
| `CLOSED → TRIAGED` | 409 — terminal state |
| `DISMISSED → FIX_PROPOSED` | 409 — terminal state |
| `APPLIED → TRIAGED` | 409 — backward transition |

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

- All subsequent `POST /api/v1/bugcheck/runs/{run_id}/findings` return **409 Conflict**
- All subsequent `POST /api/v1/bugcheck/runs/{run_id}/progress` return **409 Conflict**
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
| Redis down | Cache reads degrade to DB or miss; authority-adjacent checks fall back to DB; rate limiting and token revocation fail closed (deny) |
| Embedding provider down | Document write returns 202 (accepted); chunking queued for retry; search returns existing results without new document |
| Celery down | Async tasks queued in DLQ; synchronous path used as fallback where possible |

**Safe fail-open exceptions:** None for authority or access control. Cache may degrade performance, but it never widens permissions or bypasses revocation/rate-limit decisions.

---

## Compliance Deletion (GDPR / CCPA)

Historical docs described a multi-step erasure workflow here. The current canonical audit does
not treat that older flow or its former dedicated test file as verified repo truth. Any GDPR
or CCPA deletion contract should be re-documented only after the live implementation and test
surface are re-audited.

---

# §9 — Technology Stack

## Runtime Environment

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Typed FastAPI service; mixed async endpoints with synchronous ORM/session usage |
| FastAPI | 0.109.0 | ASGI framework; lifespan for startup/shutdown |
| uvicorn | 0.27.0 | ASGI worker server used behind Gunicorn in production |
| gunicorn | 21.2.0 | Production process manager for multiple Uvicorn workers |

## Databases

| Component | Version | Notes |
|-----------|---------|-------|
| PostgreSQL | 13+ | Primary relational store; JSONB, TSVECTOR, arrays |
| pgvector | 0.2.4 | Vector similarity extension; IVFFlat ANN index |
| Redis | 6+ | Cache, rate limiting, session data |

## ORM & Migrations

| Component | Version | Notes |
|-----------|---------|-------|
| SQLAlchemy | 2.0.36 | Core ORM; synchronous engine/session model in the current app |
| psycopg2-binary | 2.9.10 | PostgreSQL driver |
| Alembic | 1.13.1 | Schema migrations; 47 version files in `alembic/versions/` as of 2026-04-03 |

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
| uvicorn | 0.27.0 | ASGI worker implementation |
| gunicorn | 21.2.0 | Multi-worker production entrypoint on Render |

## Observability

| Component | Notes |
|-----------|-------|
| Logging stack | Structured JSON logging plus correlation IDs on the mounted app surface |
| Security headers / timeout middleware | Active in the mounted FastAPI app |
| OpenTelemetry / metrics helpers | Present in source, but the tracing/metrics routers are not mounted by default |

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

# §10 — Ecosystem Integration Contracts

This section describes the current mounted integration boundary, not every historical router
module present in the repo.

## Integration Principles

1. **Every durable-write caller authenticates.** Unauthenticated writes are not part of the contract.
2. **Scope is enforced, not implied.** Run-scoped and admin-scoped flows remain explicit.
3. **DataForge is the record.** Downstream services may cache, but they do not own truth.
4. **Unavailable means unavailable.** Readiness failure should block authority-dependent work.

## Current Integration Map

| Service or function | Current mounted prefixes | Primary responsibility in DataForge |
|---------------------|--------------------------|-------------------------------------|
| NeuroForge | `/api/neuroforge`, `/api/v1/runs`, `/api/v1/learning` | Inference persistence, routing decisions, execution logs, learning feedback |
| VibeForge | `/api/vibeforge`, `/api/teams` | Project/session/outcome persistence plus team insights |
| AuthorForge | `/api/projects` | Project, chapter, scene, manuscript, map, asset, collection, and story structure persistence |
| ForgeAgents | `/api/v1/agents`, `/api/v1/forge-run`, `/api/v1/experience` | Agent registry, run evidence, execution history, experience store |
| BugCheck | `/api/v1/bugcheck` | Run creation, finding ingest, enrichments, lifecycle events, progress |
| Forge:SMITH | `/api/v1/smithy/planning`, `/api/v1/smithy/portfolio` | Planning session state, deliverables, portfolio, evaluation evidence |
| ForgeCommand / operator control | `/admin/api-keys`, `/admin/token`, `/secrets`, governance/promotion routes | Key rotation, secret sync, runtime governance, operator-controlled approvals |
| Sentinel | `/api/v1/sentinel` | Persist sweep records and healing-event records |
| PressForge | `/api/v1/press` | Automation jobs, runs, logs, overrides, media workflows, campaign state |
| Pricing / provider governance | `/api/v1/models`, `/api/v1/pricing`, `/api/v1/costs`, `/api/v1/batch`, `/api/v1/rate-limits` | Catalog, pricing snapshots, cost ledgers, batch queue, rate-limit state |
| Policy and runtime shaping | `/api/v1/policy-envelopes`, `/api/v1/policy-runs`, `/api/v1/policy-routing`, `/api/v1/runtime-promotion` | Deterministic policy envelopes, ledgers, reward records, runtime-promotion receipts/candidates |
| Diligence / events / telemetry / Tarcie | `/api/diligence`, `/api/v1/events`, `/api/v1/telemetry/events:batch`, `/ingest/tarcie` | Compliance review records, BuildGuard events, authenticated generic operational telemetry, friction ingest |

Forge:SMITH and other non-Python applications use the authenticated telemetry HTTP boundary; they
never receive DataForge/PostgreSQL credentials. The request event is the shared
`forge_telemetry.TelemetryEvent` v0.3 model with ingress-specific batch and JSON
complexity bounds. The FT-02 authority copy pins the complete redacted RFC 8785
event ceiling at 65,536 bytes and the violation code at
`event_size_exceeded`; `metadata` and `metrics` are not independent 64 KiB
budgets.
| Private source ingestion | `/api/v1/private-source-profiles` | Operator-curated source profile persistence |

## BugCheck Contract

BugCheck remains the most tightly governed integration surface.

| Operation | Current mounted endpoint shape | Expected authority |
|-----------|--------------------------------|--------------------|
| Create run | `POST /api/v1/bugcheck/runs` | operator/admin-controlled |
| Ingest finding | `POST /api/v1/bugcheck/runs/{run_id}/findings` | run-scoped |
| Batch ingest findings | `POST /api/v1/bugcheck/runs/{run_id}/findings/batch` | run-scoped |
| Append progress | `POST /api/v1/bugcheck/runs/{run_id}/progress` | run-scoped |
| Append enrichment | `POST /api/v1/bugcheck/findings/{finding_id}/enrichments` | run-scoped |
| Append lifecycle event | `POST /api/v1/bugcheck/findings/{finding_id}/lifecycle` | user/operator-scoped |

Invariants:

- BugCheck findings remain run-scoped.
- Lifecycle events remain separate from finding creation.
- Finalized or otherwise closed run-state enforcement stays fail-closed at the API layer.

## NeuroForge and Learning

NeuroForge writes inference and routing evidence through `/api/neuroforge/*`, while broader
execution and learning records land under `/api/v1/runs` and `/api/v1/learning`.

Representative mounted routes:

- `POST /api/neuroforge/inferences`
- `POST /api/neuroforge/routing-decisions`
- `POST /api/v1/runs`
- `GET /api/v1/learning/model-performance`
- `GET /api/v1/learning/recommendations/*`

## Authoring, Planning, and Portfolio State

Mounted authoring and planning surfaces now span:

- `POST /api/projects` and the broader `/api/projects/{project_id}/...` family
- `POST /api/vibeforge/projects` and `/api/vibeforge/sessions`
- `POST /api/v1/smithy/planning/sessions`
- `POST /api/v1/smithy/portfolio/projects`

These surfaces are no longer "future integrations"; they are part of the live mounted app.

## Operator Control and Governance

ForgeCommand and other operator-controlled flows interact with DataForge through mounted
control surfaces, including:

- `POST /admin/api-keys/generate`
- `POST /admin/token/rotate`
- `POST /secrets/sync`
- `POST /api/v1/runtime-promotion/candidates/{candidate_id}/approve`
- `PUT /api/v1/policy-envelopes/{policy_key}`
- `POST /api/v1/policy-runs/ledger`

DataForge persists governance evidence and operator decisions; it does not replace the
external orchestration/control surface that decides when those endpoints are called.

## Sentinel Contract

Sentinel currently uses DataForge as a persistence boundary for sweeps and healing-event
records. The mounted DataForge router does **not** perform autonomous healing itself.

Representative mounted routes:

- `POST /api/v1/sentinel/sweeps`
- `PATCH /api/v1/sentinel/sweeps/{sweep_id}`
- `POST /api/v1/sentinel/healing`
- `PATCH /api/v1/sentinel/healing/{event_id}`

## Common Integration Pattern

Clients that depend on DataForge authority should check readiness first:

```python
async def check_dataforge_ready(http_client) -> bool:
    try:
        response = await http_client.get("http://localhost:8001/ready", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False
```

For append-only or governed writes, callers should treat `409` and `403` as contract
responses, not transient transport failures.

---

# §11 — Scope

**Truth class:** canonical doctrine

This `doc/system/` tree is the modular source of the **DataForge compiled system
reference**, assembled into the designation-bound artifact `doc/DTFSYSTEM.md`
(designation `DTF`) via `bash doc/system/BUILD.sh`. This chapter defines
DataForge's service authority and the boundaries that separate it from the rest
of the Forge ecosystem. DataForge is an internal Forge ecosystem service. It is
not a public product, not a SaaS offering, and nothing here asserts
public-release or production-certification status.

## DataForge Service Authority

DataForge is the **durable-truth boundary** for the Forge ecosystem — the
resident FastAPI persistence, retrieval, and governance-evidence service. Its
authority is durable and ecosystem-wide: state written here is the *canonical
record*, not a convenience mirror. Every major Forge runtime persists its
authoritative records into DataForge, and if a service cannot persist required
durable state here, the operation is **not complete** (fail-closed by design).

## What DataForge Owns

- **Durable persistence** — PostgreSQL is the authority boundary for documents,
  runs, findings, planning state, authoring assets, pricing/catalog data, policy
  ledgers, press-automation records, and private-source profiles.
- **Hybrid retrieval** — chunked documents with pgvector embeddings + full-text
  indexes, served as semantic, keyword, and RRF-fused search.
- **Scoped write enforcement** — run-scoped write flows, service-key validation,
  admin-key rotation, and admin-token-protected control surfaces (the live
  *mounted* surface; a richer secure-auth stack exists in source but is not part
  of the live contract until mounted).
- **Runtime governance evidence** — policy envelopes, policy ledgers, reward
  records, runtime-promotion receipts, candidate approvals/rejections, rate-limit
  state, and execution evidence for operator review.
- **Append-only audit truth** — the immutable, HMAC-signed audit log.

## What DataForge Does Not Own

- **Orchestration / control.** ForgeCommand is the ecosystem operator/control
  plane; DataForge does not schedule, transition lifecycles on its own behalf, or
  grant governed overrides.
- **Autonomous repair.** Sentinel records are persisted here, but DataForge does
  not itself perform remediation.
- **Cache authority.** Redis accelerates reads/rate-limits and holds derived
  state only — it never owns truth; pgvector + Postgres readiness drive the
  authoritative ready signal.
- **The live OAuth2/TOTP gateway** on the default mounted surface (those secure
  modules are source-only until explicitly wired).
- **The `forge-telemetry/` codebase.** That nested repo is versioned and
  documented separately and is out of this documentation boundary.

## Write-Boundary / Access-Control Authority

DataForge enforces *who may write what* at the API boundary: ForgeCommand writes
run records, lifecycle transitions, and finalization (admin token); BugCheck
writes findings/progress/telemetry only (run_token); XAI/MAID write enrichment
only (run_token); VibeForge writes user decisions only (user_token). After a run
is FINALIZED, new findings are rejected with 409 (run immutability). These
boundaries are invariants, not suggestions.

## Release / Readiness Language Restrictions

This documentation describes an internal service under governed development. It
must be described as a verification-current internal service, not as externally
release-certified, and must not claim public-release/SaaS readiness or present
coverage percentages as guarantees unless a later governed slice proves the
specific claim.

## Documentation truth classes

Every statement in this documentation system belongs to one of two classes:

- **Canonical facts** define DataForge's source-of-truth contract, persistence
  and retrieval authority, write-boundary/access-control invariants, fail-closed
  readiness posture, and ecosystem contracts. They change only through deliberate
  change control (§13).
- **Snapshot facts** are audit-derived counts — mounted routers, migrations,
  Python/test files, collected tests — labelled with a measurement date. They may
  drift between rebuilds and are corrected by re-measurement, not change control.

Ownership, designation doctrine, and the authority hierarchy that govern this
tree are defined in §12.

---

# §12 — Governance

**Truth class:** canonical doctrine

Ownership, review, and change-authority boundaries for this documentation
system. §11 defines DataForge's *service* authority; this chapter defines the
*documentation* authority that governs how this `doc/system/` tree is owned,
designated, and changed.

## Ownership

| Artifact | Owner |
|----------|-------|
| `doc/system/` source modules | DataForge repository (this repo) |
| `doc/DTFSYSTEM.md` compiled artifact | DataForge repository — generated, never hand-edited |
| `DTF` designation | ForgeCommand designation registry (governed registry state, not local repo opinion) |
| Ecosystem composite compiled system reference | ForgeCommand |
| `forge-telemetry/` documentation | The nested `forge-telemetry` repo (separate boundary) |

The operating context is a single-operator governed environment: compliance
state must be explicit, visible, and reconstructable; remediation is bounded and
reviewable; approval remains human-authoritative.

## Designation doctrine

- The designation is exactly three letters (`DTF`), unique across the governed
  repo registry, and stable once assigned.
- The compiled artifact filename is bound to the designation:
  `doc/{DESIGNATION}SYSTEM.md` → `doc/DTFSYSTEM.md`. `BUILD.sh` fails closed if the
  requested output path does not end in `DTFSYSTEM.md`.
- Designation changes occur only through explicit change control in the
  ForgeCommand registry, never by local edit.
- Legacy outputs (`SYSTEM.md` at repo root, `doc/dfSYSTEM.md`, two-letter prefixed
  artifacts, the bootstrap `doc/SYSTEM.md`) are non-canonical; if detected they
  are migration signals, not truth surfaces.

## Authority hierarchy

When documentation sources conflict, resolve in this order:

1. `doc/DTFSYSTEM.md` — the compiled system reference (implemented reality)
2. `CLAUDE.md` — AI implementation instructions and working rules
3. Module/schema specs and plans under `docs/`
4. README and ad-hoc notes

The compiled system reference wins because it describes implemented reality; all
other surfaces describe intent, instruction, or history. DataForge owns durable
*data* truth, but the *operator/control* authority is ForgeCommand's (§11).

## Truth-class enforcement

Every statement in this tree is a **canonical fact** (source-of-truth contract,
persistence/retrieval authority, write-boundary invariants, fail-closed posture,
ecosystem contracts — changed only through change control, §13) or a **snapshot
fact** (audit-derived counts: mounted routers, Alembic migrations, Python/test
files, collected tests — labelled with a measurement date and corrected by
re-measurement). Snapshot facts must never be promoted to guarantees;
release/readiness language is constrained per §11.

## Editing rule

Source modules under `doc/system/` are the only editing surface. The compiled
artifact is regenerated by `bash doc/system/BUILD.sh` and validated by
`doc/system/validate_snapshots.sh` during assembly. A hand edit to
`doc/DTFSYSTEM.md` is a governance violation and is overwritten by the next build.

## Enforcement

ForgeCommand is the enforcement surface for documentation compliance: discovery
of governed repos, compliance evaluation from evidence, remediation planning,
operator approval before write actions, and post-remediation rebuild
verification. Where automated enforcement is not yet wired up for this repo,
enforcement is manual but explicit: the change-control workflow in §13.

---

# §13 — Change Control

**Truth class:** canonical doctrine

This chapter defines how changes to DataForge are classified, evidenced,
verified, and rolled back. It is practical and enforceable: every change class
names the evidence and verification commands that must accompany it. DataForge is
an internal Forge ecosystem service; nothing here authorizes public-release or
production-certification claims.

## Change Classes

| Class | Scope | Example |
|-------|-------|---------|
| C0 | Documentation only | Editing `doc/system/` chapters, rebuilding `doc/DTFSYSTEM.md` |
| C1 | Schema / migration | New/changed ORM models, Alembic migrations, pgvector index |
| C2 | API surface | Mounting/altering a router, request/response contract changes |
| C3 | Retrieval | Embedding model/dimension, chunking, hybrid-search/RRF tuning |
| C4 | Write-boundary / access control | Token scopes, key rotation, run immutability, audit log |
| C5 | Runtime governance | Promotion receipts, policy envelopes, rate limits, evidence tables |
| C6 | Configuration / security | `config` env contract, encryption, secrets, readiness signals |

## Required Evidence Per Change Class

- **C0** — rebuilt artifact (`bash doc/system/BUILD.sh` → `BUILD_OK`), edited
  source chapter (never a hand-edit to `doc/DTFSYSTEM.md`).
- **C1** — the Alembic migration file + `alembic upgrade head`/`downgrade`
  applied cleanly; the migration count in §1/§9 re-measured.
- **C2** — the router mounted in `app/main.py` (or explicitly noted as
  source-present-not-mounted), with contract tests covering the new surface.
- **C3** — evidence the embedding dimension stays consistent with stored vectors
  (a dimension change is a migration, not a config tweak) and search quality is
  not silently degraded.
- **C4** — proof the access-control matrix still holds (ForgeCommand/BugCheck/
  XAI/VibeForge write scopes), run-immutability (409 after FINALIZED), and the
  audit log remains append-only + HMAC-signed.
- **C5** — the governance-evidence table/flow with operator-review surfacing.
- **C6** — the env/setting reflected in §14 (Configuration), with secrets sourced
  from the vault/secret-sync path and readiness driven by DB/pgvector (not Redis).

## Required Verification Commands

```bash
PYTHONPATH=. ./.venv/bin/pytest -q            # full suite
pytest --cov=app tests/                       # coverage
alembic upgrade head                          # schema changes (C1)
ruff check app/ && mypy app/                  # lint + types
bash doc/system/BUILD.sh                       # doc changes (C0) -> BUILD_OK designation=DTF
curl -s localhost:8001/ready                   # fail-closed readiness (DB + pgvector)
```

## Source-of-Truth / Fail-Closed Rules

DataForge stays the canonical durable record (§11): a change must not introduce a
path where a service's authoritative state is considered complete without being
persisted here. Readiness stays DB/pgvector-driven; Redis remains derived state.
The mounted surface is the live contract — adding a router to source without
mounting it does not change the contract (note it as source-present-not-mounted).

## Documentation Change Rules (C0)

`doc/system/` source modules are the only editing surface. The compiled
`doc/DTFSYSTEM.md` is regenerated, never hand-edited (§12). Snapshot facts
(router/migration/test counts) are re-measured and re-dated, not asserted as
guarantees.

## Release / Readiness Claim Rules

No change may introduce public-release, public-SaaS, or production-certification
language, or present a coverage percentage as a guarantee, unless a governed
release slice proves that specific claim.

---

# §14 — Configuration & Environment Variables

All configuration is injected via environment variables. There are no config files read at runtime beyond `.env` (loaded by the application on startup via `python-dotenv` or equivalent). The canonical reference for all variables is `.env.example` at the repository root.

## Database

| Variable | Type | Default | Required | Notes |
|----------|------|---------|----------|-------|
| `DATAFORGE_DATABASE_URL` | str | `postgresql://postgres:postgres@localhost:5432/dataforge` | YES | Canonical PostgreSQL DSN used by the app |
| `REDIS_URL` | str | `redis://localhost:6379/0` | YES | Redis connection string for derived cache/state |
| `DB_CONNECT_TIMEOUT_SECONDS` | int | `5` | NO | PostgreSQL connect timeout applied by SQLAlchemy |
| `DB_STATEMENT_TIMEOUT_MS` | int | `10000` | NO | PostgreSQL statement timeout applied to each session |
| `DB_LOCK_TIMEOUT_MS` | int | `5000` | NO | PostgreSQL lock wait timeout |
| `DB_IDLE_IN_TX_TIMEOUT_MS` | int | `15000` | NO | PostgreSQL idle-in-transaction timeout |
| `DB_POOL_SIZE` | int | `5` | NO | SQLAlchemy pool size for non-SQLite backends |
| `DB_MAX_OVERFLOW` | int | `10` | NO | SQLAlchemy overflow connection cap |
| `DB_POOL_TIMEOUT_SECONDS` | int | `10` | NO | SQLAlchemy pool checkout timeout |
| `DB_POOL_RECYCLE_SECONDS` | int | `1800` | NO | SQLAlchemy connection recycle interval |
| `DATAFORGE_SKIP_STARTUP_DB_INIT` | bool | `false` | NO | Skips the best-effort pgvector startup init. Useful in tests and as an operational escape hatch |

**Example:**
```
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
REDIS_URL=redis://localhost:6379/0
```

Never use SQLite in production. The pgvector extension requires PostgreSQL 13+.

`DataForge` no longer treats pgvector startup init as a fatal boot dependency. If the database is temporarily unavailable during startup, the service still boots, `/health` stays live, and `/ready` reports the database/pgvector failure until connectivity recovers.

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
| `REQUEST_TIMEOUT_SECONDS` | float | `30` | NO | ASGI request timeout guard; requests exceeding this return `504` |

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
| `NEUROFORGE_URL` | str | `http://127.0.0.1:8000` | NO | Preferred embedding/inference gateway |
| `VOYAGE_API_KEY` | str | — | NO | Legacy direct embedding fallback |
| `OPENAI_API_KEY` | str | — | NO | Legacy fallback provider |
| `COHERE_API_KEY` | str | — | NO | Legacy fallback provider |
| `EMBEDDING_MODEL` | str | `voyage-large-2` | NO | Voyage AI model name; 1536-dim output |

**Current runtime posture:** NeuroForge-first. Direct provider keys remain for backward
compatibility and emergency fallback paths.

If no legacy provider keys are set, the application still starts. Direct embedding fallback
is unavailable until at least one provider key is configured.

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
| `RATE_LIMIT_SEARCH` | str | `20/minute` | Search endpoint policy |
| `RATE_LIMIT_ADMIN` | str | `100/minute` | Admin endpoint policy |

Redis TTL for rate-limit records is derived as `window_length + 60s`. On Redis outage, the
rate-limit path fails closed and denies the request rather than silently allowing more traffic.

## Cache Governance

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `DOC_FETCH_CACHE_TTL` | int | `600` | Document cache TTL |
| `SEARCH_RESULTS_CACHE_TTL` | int | `300` | Retrieval/search result cache TTL |
| `EMBEDDING_RESULTS_CACHE_TTL` | int | `86400` | Embedding cache TTL |
| `SESSION_OAUTH_TOTP_CACHE_TTL` | int | `900` | OAuth/TOTP and auth-adjacent short-lived cache TTL |
| `CORPUS_CURRENT_VERSION_CACHE_TTL` | int | `60` | `corpus_version:current` cache TTL |

All Redis writes must set TTL at write time. There are no persistent cache keys by design.

## Compliance & Encryption

| Variable | Type | Notes |
|----------|------|-------|
| `ENCRYPTION_KEY` | str | AES-256 Fernet key for field-level PII encryption. Derived from `SECRET_KEY` if not set separately |
| `GDPR_DELETION_DELAY_DAYS` | int | Days before hard deletion executes after GDPR erasure request |

## NeuroForge Integration

The app-level config currently exposes:

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `NEUROFORGE_URL` | str | `http://127.0.0.1:8000` | Base URL for NeuroForge embedding/inference integration |

---

## Full `.env.example` Reference

```dotenv
# Database
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
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
NEUROFORGE_URL=http://127.0.0.1:8000
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

# Cache Governance
DOC_FETCH_CACHE_TTL=600
SEARCH_RESULTS_CACHE_TTL=300
EMBEDDING_RESULTS_CACHE_TTL=86400
SESSION_OAUTH_TOTP_CACHE_TTL=900
CORPUS_CURRENT_VERSION_CACHE_TTL=60
```

## Secrets Management

In production, secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `VOYAGE_API_KEY`, etc.) must not live in `.env` files committed to version control. Use:

- **ForgeCommand vault** — the canonical secrets source for Forge services
- **Docker secrets** — for container deployments
- **Kubernetes Secrets** — for k8s deployments (sealed or external-secrets operator)

LLM API keys are synced to DataForge from the ForgeCommand vault via the `/secrets` router. Services retrieve API keys through DataForge at runtime; keys never cross the IPC boundary in plaintext.

---

# §15 — Testing

*Last updated: 2026-04-04*

## Current Audited Snapshot

| Metric | Value |
|--------|-------|
| Total test files | `40` |
| Total tests collected | `594` (565 baseline + 29 proving-slice) |
| Inventory command | `PYTHONPATH=. venv/bin/python -m pytest --collect-only -q` |
| Inventory audit date | `2026-04-04` |
| Coverage config | branch coverage enabled in `pytest.ini` |

This section intentionally documents what is currently observable from the repository. It
does not restate historical phase-era coverage claims or assume a full green environment
without PostgreSQL or Redis.

## Current Suite Shape

### API / HTTP Regression

- `tests/test_api/test_admin_endpoints.py`
- `tests/test_api/test_agents_registry_endpoints.py`
- `tests/test_api/test_auth_endpoints.py`
- `tests/test_api/test_health_endpoints.py`
- `tests/test_api/test_press_automation.py`
- `tests/test_api/test_request_timeout_middleware.py`
- `tests/test_api/test_search_endpoints.py`
- `tests/test_api/test_sentinel_endpoints.py`
- `tests/test_api/test_vibeforge_endpoints.py`

### Integration / Workflow

- `tests/test_dataforge_integration.py`
- `tests/test_integration/test_api_endpoints.py`
- `tests/test_integration/test_crud_operations.py`
- `tests/test_integration/test_e2e_workflows.py`
- `tests/test_integration/test_infrastructure_health.py`

### Proving-Slice Intake

- `tests/test_proving_slice_intake.py` — 29 tests covering accepted (8), rejected (5), duplicate/idempotency (3), family gate (3), receipt lookup (4), and adversarial (6). Adversarial tests exercise real contract-core validation without patching. No live DB required (SQLite in-memory via conftest).

### Runtime / Governance / Persistence

- `tests/test_cache_governance.py`
- `tests/test_circuit_breaker.py`
- `tests/test_corpus_governance.py`
- `tests/test_db_replication.py`
- `tests/test_dlq_and_retry.py`
- `tests/test_experience.py`
- `tests/test_policy_envelope_router.py`
- `tests/test_policy_envelope_seed.py`
- `tests/test_rate_limiter.py`
- `tests/test_rate_limits.py`
- `tests/test_runtime_promotion_candidates.py`
- `tests/test_runtime_promotion_execution_worker.py`
- `tests/test_seed_model_catalog.py`
- `tests/test_sql_integration.py`
- `tests/test_token_revocation.py`

### Unit / Security / Load

- `tests/test_security/test_vulnerability_scanning.py`
- `tests/test_unit/test_auth.py`
- `tests/test_unit/test_embeddings.py`
- `tests/test_unit/test_main_startup.py`
- `tests/test_unit/test_models.py`
- `tests/test_unit/test_rate_limit.py`
- `tests/test_unit/test_vibeforge_schemas.py`
- `tests/test_unit/test_vibeforge_services.py`
- `tests/load/test_k6_load.py` (opt-in load surface)

## Running the Suite

### Inventory Only

```bash
PYTHONPATH=. ./.venv/bin/pytest --collect-only -q
```

### Full Repo Suite

```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest -q
```

### With Coverage

```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest --cov=app tests/ --cov-report=term-missing
```

### Focused Governance Surfaces

```bash
.venv/bin/pytest tests/test_policy_envelope_router.py tests/test_runtime_promotion_candidates.py -v
```

## Environment Notes

- Many tests expect a real PostgreSQL database and, for some cases, Redis or pgvector support.
- `tests/load/test_k6_load.py` is opt-in and remains a non-default load surface.
- `tests/test_integration/test_infrastructure_health.py` and other infra-sensitive suites may skip when local dependencies are absent.
- The policy-envelope handlers remain synchronous by design, matching the production app's sync SQLAlchemy usage inside FastAPI.

## `pytest.ini`

The repo root `pytest.ini` is the canonical test configuration surface. It enables:

- `--strict-markers`
- branch coverage reporting
- `asyncio_mode = auto`
- centralized `tests/` discovery

When documenting test totals, prefer the audited collect-only command above over historical
phase summaries.

---

# §16 — Handover, Critical Constraints & Migration Runbook

## Critical Invariants — Never Violate These

These are architectural invariants, not guidelines. Violating them causes data loss, security breaches, or ecosystem-wide consistency failures.

### 1. DataForge Is the Only Source of Truth

No service maintains authoritative state outside DataForge/Postgres. There is no "eventually
consistent" model. There is no "local cache that syncs later." If the authoritative write fails,
the operation fails. Period.

```
WRONG: Service stores finding in local DB, syncs to DataForge later
RIGHT: Service attempts DataForge write; if it fails, the operation fails
```

Redis is explicitly derived state only. It can accelerate reads, but it cannot own authority.

### 2. Cache Must Never Decide Authority

Auth, permission, revocation, and rate-limit outcomes must always be derivable from the
authoritative database path or signed evidence. Redis misses and Redis errors must never turn
into "allow".

### 3. No Redis Writes Without TTL

Every Redis write must include TTL at write time. If a record needs to outlive TTL semantics,
it belongs in Postgres instead.

### 4. Corpus Versioning Must Stay Monotonic and Atomic

Retrieval cache invalidation depends on `corpus_state.current_version`. Bumps must remain a
single `UPDATE ... RETURNING` plus append-only audit insert. Do not replace this with a scan,
`SELECT MAX(version)`, or any non-atomic pattern.

### 5. run_token Scope Cannot Be Widened

A run_token issued for `run_id=abc` cannot be used to write findings to `run_id=xyz`. The DataForge API validates the `run_id` claim in the token against the path parameter on every request. Do not attempt to "share" tokens across runs.

### 6. Lifecycle Transitions Are One-Way (With One Exception)

Once a finding reaches a terminal state (`CLOSED` or `DISMISSED`), no further transitions are possible. The only "reset" path is to re-run BugCheck — which produces new findings, not new states on old ones.

### 7. The Audit Log Is Append-Only Forever

There is no admin endpoint to delete audit log entries. There is no SQL DELETE on the events table in any migration. If you find code attempting to DELETE from the audit log, treat it as a security incident.

### 8. After FINALIZED, Run Records Are Immutable

The `status = "finalized"` transition is one-way. ForgeCommand sets it; nothing can unset it. Attempts to write findings to a finalized run return 409. This is by design — finalization is a commitment to the record.

### 9. Field Encryption Key Rotation Requires a Migration

Changing `SECRET_KEY` (and thus the derived Fernet key) without a migration or dedicated
rotation utility will make existing encrypted field values unreadable. Never rotate the secret
key unless the re-encryption path is implemented and reviewed in the repo you are deploying.

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

# 1. Install any new dependencies
.venv/bin/pip install -r requirements.txt

# 2. Run migrations
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/alembic upgrade head

# 2a. Refresh the canonical model catalog when model identifiers or pricing change
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/python scripts/seed_model_catalog.py

# 2b. Refresh governed policy whitelists after catalog changes
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/python scripts/seed_policy_envelopes.py

# 3. Verify migrations applied cleanly
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/alembic current

# 4. Run tests to confirm nothing broke
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest -q

# 5. Start service
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

For migration-sensitive changes, the preferred validation loop is:

```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/alembic upgrade head
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest -q
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/alembic downgrade -1
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/alembic upgrade head
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

1. Define the SQLAlchemy model class in the correct module under `app/models/`
2. Define the corresponding Pydantic schemas in the matching `*_schemas.py` module
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
- [ ] `DATAFORGE_DATABASE_URL` set in `.env`
- [ ] `REDIS_URL` set in `.env`
- [ ] `SECRET_KEY` set to a 32-char hex value
- [ ] `NEUROFORGE_URL` reachable
- [ ] `alembic upgrade head` run
- [ ] Admin user created via `scripts/create_admin.py`
- [ ] `GET /health` returns 200
- [ ] `GET /ready` returns 200 before running dependent-service smoke tests

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
- [ ] Production start command uses Gunicorn with Uvicorn workers
- [ ] Health check endpoint registered with load balancer / Render as `/health`
- [ ] Grafana dashboards imported
- [ ] Backup schedule confirmed (daily/weekly/monthly + PITR)

If Postgres or the pgvector extension is unreachable during a deploy, `DataForge` should still boot and bind a port. Treat `/ready` as the authoritative signal for database/pgvector availability; do not revert to a startup path that exits the worker before `/health` can respond.
- [ ] `alembic upgrade head` run against production DB before traffic cutover
- [ ] Smoke test: `GET /health`, `GET /ready`, `POST /auth/token`, `POST /api/search`

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

Check Redis is running: `redis-cli ping`. Expect performance degradation, cache-miss behavior,
and explicit degradation logs. Do not "fix" the issue by allowing cache-dependent security
decisions to bypass the authoritative DB path.

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
uvicorn (N workers) → PgBouncer (pool_size=20) → PostgreSQL
```

Adjust `DATABASE_URL` to point to PgBouncer's port (default: 6432).

### Redis Memory

Monitor Redis memory usage. Tune TTLs through the cache-governance helpers and whichever
mounted consumers are actually using Redis-backed derived state. If Redis memory exceeds
80% of limit, reduce TTLs or increase memory allocation.

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `/home/charlie/Forge/ecosystem/DataForge/app/main.py` | FastAPI app, router registration, lifespan |
| `/home/charlie/Forge/ecosystem/DataForge/app/database.py` | SQLAlchemy engine, session factory |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/models.py` | Core shared ORM tables only |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/schemas.py` | Core shared schemas only |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/` | Full modular model/schema catalog for domains, governance, and platform surfaces |
| `/home/charlie/Forge/ecosystem/DataForge/app/api/crud.py` | Database operations |
| `/home/charlie/Forge/ecosystem/DataForge/app/api/search.py` | Hybrid search implementation |
| `/home/charlie/Forge/ecosystem/DataForge/app/utils/embeddings.py` | Chunking + embedding generation |
| `/home/charlie/Forge/ecosystem/DataForge/app/utils/auth.py` | JWT + bcrypt utilities |
| `/home/charlie/Forge/ecosystem/DataForge/alembic/versions/` | Migration history |
| `/home/charlie/Forge/ecosystem/DataForge/tests/` | 54 test files; 730 collected tests in the 2026-07-14 inventory audit |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/multi_provider_models.py` | Multi-provider pipeline models (6 tables) |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/sentinel_models.py` | Sentinel health + healing models |
| `/home/charlie/Forge/ecosystem/DataForge/app/api/sentinel_router.py` | Sentinel sweep + healing REST API |
| `/home/charlie/Forge/ecosystem/DataForge/scripts/seed_model_catalog.py` | Canonical model catalog seed script; retires stale xAI aliases |
| `/home/charlie/Forge/ecosystem/DataForge/.env.example` | All env vars documented |
| `/home/charlie/Forge/ecosystem/DataForge/requirements.txt` | Pinned dependencies |

---

## Documentation Audit Note

The current canonical reference is the generated root `SYSTEM.md` assembled from `doc/system/`.
When older phase summaries or historical completion documents conflict with the generated
system docs, the generated system docs win.

---

*Forge Documentation Protocol v1 — Last updated: 2026-04-03*

---

# §17 — Appendices

**Document version:** 1.0 (carry-forward)

Appendices, glossary, and cross-references.

## Revision history

| Version | Date | Change |
|---------|------|--------|
| 2.0 | 2026-06-19 | Migrated the compiled reference to the BDS canonical-compliance documentation structure. |
| 2.1 | 2026-07-23 | Documented the authority-pinned FT-02 65,536-byte complete canonical telemetry-event boundary and stable `event_size_exceeded` behavior. |

## Unmapped legacy chapters

The following legacy chapters were carried forward but could not be
deterministically mapped to a class-aware slot. Review and place them by
hand:

- `DataForge System Documentation`
- `§3 — Technology Stack`
- `§5 — Configuration & Environment Variables`
- `Database`
- `Security`
- `Server`
- `AI Providers`
- `Chunking`
- `Logging`
- `§6 — API Layer`
- `§7 — Backend Internals`
- `pgvector cosine similarity query`
- `PostgreSQL TSVECTOR + ts_rank`
- `§8 — Ecosystem Integration Contracts`
- `§9 — Error Handling, Lifecycle & Access Control`
- `Default fingerprint`
- `Category-specific fingerprints`
- `API Contract Drift:`
- `Dependency CVE:`
- `Flaky Test:`
- `§10 — Testing`
- `§11 — Handover, Critical Constraints & Migration Runbook`
- `1. Install any new dependencies`
- `2. Run migrations`
- `2a. Refresh the canonical model catalog when model identifiers or pricing change`
- `2b. Refresh governed policy whitelists after catalog changes`
- `3. Verify migrations applied cleanly`
- `4. Run tests to confirm nothing broke`
- `5. Start service`
- `Auto-generate migration from ORM model changes`
- `Review the generated file in alembic/versions/`
- `Verify the upgrade() and downgrade() functions are correct`
- `Apply`
- `Verify`
- `Roll back one step`
- `Roll back to a specific revision`
- `View migration history`
- `Create admin user interactively`
- `Or set environment variables for non-interactive:`
- `§13 — Proving-Slice Schema`
