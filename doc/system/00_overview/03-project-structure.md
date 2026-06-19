# §3 — Project Structure

## Directory Tree

*Last updated: 2026-04-04*

```
DataForge/
├── alembic/                          # Database migration history
│   ├── env.py                        # Alembic environment config (imports ORM models)
│   ├── script.py.mako                # Migration template
│   └── versions/                     # 47 migration version files (hash-prefixed Alembic names)
│
├── app/                              # Main application package (175 Python files)
│   ├── main.py                       # FastAPI app + lifespan + router registration (35 mounted routers)
│   ├── database.py                   # SQLAlchemy engine, SessionLocal, get_db()
│   ├── config.py                     # Environment config and validation
│   ├── security_config.py            # Security policy helpers
│   ├── logging_config.py             # Structured logging setup
│   │
│   ├── models/                       # ORM models + Pydantic schemas (52 files, 27 domain families)
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
│   │   ├── team_models.py / _schemas.py                # Team and organization state
│   │   └── vibeforge_models.py / _schemas.py           # VibeForge projects, sessions, analytics
│   │
│   ├── api/                          # Router modules (40+ files; 35 mounted in main.py)
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
│   └── utils/                        # Shared utility modules (27 files)
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
├── tests/                            # 39 test files, 565 collected tests as of 2026-04-03
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
│   └── ... (39 files total)
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
The FastAPI application entry point. Defines the `lifespan` context manager (configuration validation, pgvector init, shutdown cleanup). Registers the 35 currently mounted router objects, configures CORS and request-timeout middleware, mounts `static/` when present, and registers exception handlers.

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
47 migration files covering the base schema plus later domain additions, pgvector support,
pipeline tables, Sentinel tables, private source profiles, and corpus-governance state.
Always run `alembic upgrade head` after pulling new code.
