# DataForge — Claude Code Context

## Service Identity

**What it is:** Resident FastAPI service and durable-truth boundary for the Forge ecosystem.
**What it does:** Persists authoritative state, serves hybrid retrieval, and stores operator/runtime governance evidence.
**Port:** 8001
**Location:** `/home/charlie/Forge/ecosystem/DataForge/`
**Entry point:** `app/main.py`
**Status:** Resident FastAPI service; documentation refreshed against the 2026-07-24 CP2 working tree (`45` mounted router objects, `66` Alembic migrations, `60` pytest files / `791` collected tests)

## CRITICAL RULES (NON-NEGOTIABLE)

1. **DataForge owns approved DataForge-domain durable state.** AuthorForge is the explicit
   exception: its embedded database exclusively owns projects and user content. DataForge may
   receive only strict minimized `AuthorForgeAnalyticsEnvelope.v1` telemetry—never content,
   identity, paths, raw logs, prompts/responses, attachments, or embeddings.
2. **BugCheck writes findings only.** Requires `run_token` scoped to `{run_id, targets, mode, scope, commit_sha}`.
3. **BugCheck NEVER writes lifecycle transitions.** Only ForgeCommand writes those.
4. **VibeForge NEVER writes findings.** Only user decisions.
5. **Audit log is immutable.** Append-only with HMAC-SHA256 signatures. Never modify.
6. **After FINALIZED, reject new findings with 409.** Run immutability is enforced at API level.

## Architecture at a Glance

```
DataForge (Source of Truth for approved domains; AuthorForge content stays local)
├── PostgreSQL 13+ with pgvector extension (1536-dim IVFFlat index)
├── Redis 6+ (cache, sessions, rate limiting, distributed lock)
├── Hybrid search: semantic cosine distance + BM25 keyword → RRF fusion (+40% accuracy)
├── 45 mounted router objects in `app/main.py`
├── Additional router modules exist in `app/api/` and stay inactive until explicitly mounted
├── 214 Python files under `app/` plus a separate sibling `../forge-telemetry/` library repo
├── 66 Alembic migration files under `alembic/versions/`
├── Modular `app/models/` layout with domain-specific `*_models.py` and `*_schemas.py` files
└── Policy/runtime governance surfaces: promotion receipts, policy envelopes, rate limits, Sentinel, secrets, press, private source
```

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app with lifespan management (CORS, routers, static) |
| `app/database.py` | SQLAlchemy engine + synchronous session dependency |
| `app/models/models.py` | Core shared ORM tables only |
| `app/models/schemas.py` | Core shared schemas only |
| `app/models/` | Modular model/schema catalog; AuthorForge content mappings are legacy migration/audit-only |
| `app/api/search_router.py` | Public search: `POST /api/search`, `GET /api/search/stats` |
| `app/api/admin_router.py` | Admin CRUD: domains, documents (auto-chunk+embed), tags |
| `app/api/auth_router.py` | `/auth/token` plus legacy `/api/auth` login/register/refresh/me routes |
| `app/api/crud.py` | Database operations layer |
| `app/api/search.py` | Vector similarity + BM25 hybrid search logic |
| `app/telemetry_client.py` | Privacy-bounded canonical ForgeEvent.v1 search producer, opt-in CP2 recovery spool, and bounded transport lifecycle |
| `app/telemetry_database.py` | CP2 least-privilege telemetry DB role preflight, isolated two-connection pool, timeouts, and per-process rate budget |
| `app/utils/embeddings.py` | Text chunking (500 tokens, 50 overlap) + embedding generation |
| `app/utils/auth.py` | JWT signing + bcrypt password hashing |
| `alembic/` | Database migrations (`63` migration files as of 2026-07-20) |
| `scripts/create_admin.py` | Interactive admin user creation |
| `templates/admin.html` | Self-contained admin UI (no external deps) |
| `../forge-telemetry/` | Sibling shared-library repo with its own documentation boundary and build surfaces |

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI 0.109+, Pydantic v2, uvicorn
- **Database:** PostgreSQL 13+ (psycopg2-binary 2.9.10), SQLAlchemy 2.0.36
- **Vector Search:** pgvector 0.2.4 (1536-dim vectors, IVFFlat, cosine distance)
- **Cache:** Redis 6+ (Sentinel-managed, persistence enabled)
- **Embeddings:** Voyage AI voyage-large-2 (recommended), OpenAI, Cohere fallback
- **Auth:** python-jose 3.3.0 (JWT/JWE/JWS), passlib + bcrypt 4.1.2
- **Migrations:** Alembic 1.13.1
- **Testing:** pytest 7.4, pytest-asyncio, pytest-cov, `60` repo test files / `791` collected tests (`python -m pytest --collect-only -q --no-cov` on 2026-07-24)

## Development Commands

```bash
# Docker (recommended for local dev)
docker-compose up -d
docker-compose exec dataforge python scripts/create_admin.py
open http://localhost:8001/admin-ui

# Manual
python -m uvicorn app.main:app --reload --port 8001

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Tests
pytest tests/ -v
pytest --cov=app tests/

# Linting
ruff check app/
mypy app/

# Health check
curl http://localhost:8001/health
```

## Mounted API Families

| Family | Source Modules | Purpose |
|--------|----------------|---------|
| Search & Admin | `search_router`, `admin_router` | Hybrid retrieval plus core document/domain CRUD |
| Auth & Key Control | `auth_router`, `admin_keys_router`, `auth_info_router`, `rotation_router` | JWT/login compatibility, service-key governance, admin token rotation |
| AuthorForge Boundary | `authorforge_boundary_router`, `events_router` | `410` content tombstone plus strict analytics-only intake |
| Planning | `smithy_planning_router`, `smithy_portfolio_router` | Forge:SMITH persistence surfaces |
| Runtime Governance | `runtime_promotion_router`, `runtime_promotion_candidate_router`, `policy_envelope_router`, `diligence_router`, `diligence_ui_router` | Promotion receipts, candidate review, policy evidence, diligence workflows |
| Agent & Run Persistence | `forge_run_router`, `agents_registry_router`, `bugcheck_router`, `runs_router`, `experience_router` | Agent registry, run evidence, BugCheck findings, experience storage |
| Service Integrations | `neuroforge_router`, `vibeforge_router`, `learning_router`, `teams_router`, `events_router`, `telemetry_router`, `tarcie_router`, `secrets_router` | Cross-product persistence, authenticated operational telemetry, and operator-facing integrations |
| Platform Surfaces | `multi_provider_router`, `rate_limits_router`, `sentinel_router`, `compression_router`, `press_router`, `private_source_router`, `fpvs_router` | Pricing/catalog, cross-run rate limits, health sweeps, compression, press, private-source profiles, health/version probes |

Source-present but not mounted by default in `app/main.py`: `projects_router`,
`authorforge_v2_router`, `api_deployment_router`, `auth_revocation_router`,
`auth_secure_router`, `cache_replication_router`, `dlq_router`, `rate_limit_router`,
`replication_router`, `tracing_router`. The two AuthorForge content routers are retired and must
not be remounted.

## Environment Variables (Critical)

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_hex(32))">
JWT_SECRET_KEY=<same-as-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
VOYAGE_API_KEY=<from voyage.ai>         # Recommended embedding provider
OPENAI_API_KEY=<fallback embeddings>
HOST=127.0.0.1
PORT=8001
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
CHUNK_SIZE=500
CHUNK_OVERLAP=50
EMBEDDING_MODEL=voyage-large-2
MAX_EMBEDDING_INPUT_LENGTH=8000
LOG_LEVEL=INFO
```

## Access Control Matrix

| Component | Authorized Writes | Requires |
|-----------|-------------------|---------|
| ForgeCommand | run records, lifecycle transitions, finalization | admin token |
| BugCheck | findings, progress events, check telemetry | run_token (30-60 min) |
| XAI/MAID | enrichment artifacts only | run_token |
| VibeForge | user decisions only | user_token |

## Vector Search Configuration

- **Dimensions:** 1536 (voyage-large-2) or 1024 (voyage-2)
- **Index:** IVFFlat (approximate nearest neighbor)
- **Distance metric:** Cosine
- **Default similarity threshold:** 0.7
- **Max search limit:** 100 results
- **Chunking:** 500 tokens with 50-token overlap
- **Hybrid search:** Reciprocal Rank Fusion (RRF) combining semantic + BM25

## Security Notes

- Field-level AES-256 encryption for PII (auto-detected per model definition)
- 6 anomaly detectors: impossible travel, brute force, bulk exfiltration, suspicious patterns, after-hours, bulk mutations
- Compliance: GDPR, CCPA, HIPAA, SOC2, PCI-DSS
- TLS 1.3 in transit, Fernet encryption at rest for sensitive fields
- Secure OAuth2/TOTP auth modules exist in source, but `auth_secure_router` is not mounted in the default app surface

## Context Bundle

```bash
./scripts/context-bundle.sh --list
./scripts/context-bundle.sh --dry-run --preset core
./scripts/context-bundle.sh --dry-run --preset api
./scripts/context-bundle.sh --dry-run --preset schema
./scripts/context-bundle.sh --dry-run --preset testing --with-specs
```

Full system documentation: `doc/DTFSYSTEM.md` (designation DTF) built from `doc/system/` via `bash doc/system/BUILD.sh` — the canonical, fail-closed assembled reference.
