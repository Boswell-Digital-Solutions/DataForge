# §4 — Project Structure

## Directory Tree

```
DataForge/
├── alembic/                          # Database migration history
│   ├── env.py                        # Alembic environment config (imports ORM models)
│   ├── script.py.mako                # Migration template
│   └── versions/                     # 47 migration version files as of 2026-04-03
│       ├── 0001_initial_schema.py
│       ├── ...
│       ├── 0012_multi_provider_tables.py
│       ├── 0013_sentinel_tables.py
│       └── corpus_governance_001.py  # corpus_state + corpus_versions
│
├── app/                              # Main application package
│   ├── main.py                       # FastAPI app + lifespan + router registration
│   ├── database.py                   # SQLAlchemy engine, SessionLocal, get_db()
│   │
│   ├── models/
│   │   ├── models.py                 # Core shared ORM tables: users, documents, corpus state, execution index
│   │   ├── schemas.py                # Core shared schemas: auth, search, user/domain/document/tag flows
│   │   ├── multi_provider_models.py  # Multi-provider pipeline models (6 tables)
│   │   ├── multi_provider_schemas.py # Multi-provider Pydantic schemas
│   │   ├── sentinel_models.py        # Sentinel health sweep + healing models
│   │   ├── sentinel_schemas.py       # Sentinel Pydantic schemas
│   │   ├── private_source_models.py  # PSIM: PrivateSourceProfile table
│   │   └── private_source_schemas.py # PSIM: PSPCreate/Update/Response schemas
│   │
│   ├── api/
│   │   ├── search_router.py          # Mounted: POST /api/search, GET /api/search/stats
│   │   ├── admin_router.py           # Mounted: admin CRUD for documents, domains, tags
│   │   ├── auth_router.py            # Mounted: /auth/token plus legacy /api/auth login/register/refresh/me
│   │   ├── crud.py                   # Database operations (no business logic)
│   │   ├── search.py                 # Hybrid vector + BM25 search logic
│   │   ├── multi_provider_router.py  # Mounted: /api/v1/models, pricing, costs, batch queue
│   │   ├── sentinel_router.py        # Mounted: Sentinel sweep/healing record persistence
│   │   ├── private_source_crud.py    # PSIM: PrivateSourceProfile CRUD ops
│   │   └── private_source_router.py  # Mounted: /api/v1/private-source-profiles
│   │
│   └── utils/
│       ├── cache_governance.py       # TTL enforcement, deterministic keys, fail-closed cache helpers
│       ├── corpus_versioning.py      # Atomic corpus version bump + current-version cache
│       ├── embeddings.py             # Text chunking + embedding generation/cache
│       └── auth.py                   # JWT creation/validation + bcrypt helpers
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
