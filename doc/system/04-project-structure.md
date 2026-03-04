# §4 — Project Structure

## Directory Tree

```
DataForge/
├── alembic/                          # Database migration history
│   ├── env.py                        # Alembic environment config (imports ORM models)
│   ├── script.py.mako                # Migration template
│   └── versions/                     # Migration version files
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
│   │   ├── models.py                 # SQLAlchemy ORM models (31+ classes)
│   │   ├── schemas.py                # Pydantic request/response schemas (90+)
│   │   ├── multi_provider_models.py  # Multi-provider pipeline models (6 tables)
│   │   ├── multi_provider_schemas.py # Multi-provider Pydantic schemas
│   │   ├── sentinel_models.py        # Sentinel health sweep + healing models
│   │   ├── sentinel_schemas.py       # Sentinel Pydantic schemas
│   │   ├── private_source_models.py  # PSIM: PrivateSourceProfile table
│   │   └── private_source_schemas.py # PSIM: PSPCreate/Update/Response schemas
│   │
│   ├── api/
│   │   ├── search_router.py          # POST /api/search, GET /api/search/stats
│   │   ├── admin_router.py           # Admin CRUD: documents, domains, tags
│   │   ├── auth_router.py            # JWT, OAuth2, TOTP 2FA endpoints
│   │   ├── crud.py                   # Database operations (no business logic)
│   │   ├── search.py                 # Hybrid vector + BM25 search logic
│   │   ├── multi_provider_router.py  # /api/v1/models, pricing, costs, batch queue
│   │   ├── sentinel_router.py        # Sentinel sweeps + healing events CRUD
│   │   ├── private_source_crud.py   # PSIM: PrivateSourceProfile CRUD ops
│   │   └── private_source_router.py # PSIM: /api/v1/private-source-profiles
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
├── tests/                            # 31 test files, 529 collected tests as of 2026-03-01
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
The FastAPI application entry point. Defines the `lifespan` context manager (configuration validation, pgvector init, shutdown cleanup). Registers all routers with their prefixes. Configures CORS and request-timeout middleware, mounts `static/` when present, and registers exception handlers.

**Critical:** The order of router registration matters. Auth routes must be registered before protected routes. The health endpoint (`/health`) must be registered without auth middleware.

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
Contains the core SQLAlchemy ORM model classes. Key models:

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | Auth identity (username, email, hashed_password, is_admin) |
| `Domain` | `domains` | Knowledge organization hierarchy |
| `Document` | `documents` | Content storage + publication state + metadata JSONB |
| `Chunk` | `chunks` | Text segments + pgvector embedding + TSVECTOR |
| `CorpusState` | `corpus_state` | Single-row current retrieval corpus version |
| `CorpusVersion` | `corpus_versions` | Append-only audit trail of corpus version bumps |
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
| `PrivateSourceProfile` | `private_source_profiles` | PSIM: operator-curated crawl configurations |

### `app/models/schemas.py`
Pydantic v2 schemas (130+) for request/response validation. Each domain has Create, Update, and Response schemas. All schemas use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.

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
Migration files covering the base schema plus later domain additions, pgvector support,
pipeline tables, Sentinel tables, private source profiles, and corpus-governance state.
Always run `alembic upgrade head` after pulling new code.
