# DataForge — Claude Code Context

## Service Identity

**What it is:** Unified data and knowledge engine — the single source of truth for the Forge Ecosystem.
**What it does:** PostgreSQL + pgvector + Redis for persistent intelligent storage and semantic retrieval.
**Port:** 8001
**Location:** `/home/charlie/Forge/ecosystem/DataForge/`
**Entry point:** `app/main.py`
**Status:** v5.2 — 18/18 phases complete, 296 tests passing, 82% coverage

## CRITICAL RULES (NON-NEGOTIABLE)

1. **DataForge owns all durable state.** All Forge services (ForgeAgents, NeuroForge, VibeForge, AuthorForge, Forge:SMITH) write to DataForge. Nowhere else.
2. **BugCheck writes findings only.** Requires `run_token` scoped to `{run_id, targets, mode, scope, commit_sha}`.
3. **BugCheck NEVER writes lifecycle transitions.** Only ForgeCommand writes those.
4. **VibeForge NEVER writes findings.** Only user decisions.
5. **Audit log is immutable.** Append-only with HMAC-SHA256 signatures. Never modify.
6. **After FINALIZED, reject new findings with 409.** Run immutability is enforced at API level.

## Architecture at a Glance

```
DataForge (Source of Truth)
├── PostgreSQL 13+ with pgvector extension (1536-dim IVFFlat index)
├── Redis 6+ (cache, sessions, rate limiting, distributed lock)
├── Hybrid search: semantic cosine distance + BM25 keyword → RRF fusion (+40% accuracy)
├── 29 domain-specific API routers across all Forge products
├── 80+ REST endpoints
├── 133 Python files, 42,732 lines of code
├── Field-level AES-256 encryption for PII (auto-detected by model)
└── Multi-tenant RBAC with anomaly detection (6 detector types)
```

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app with lifespan management (CORS, routers, static) |
| `app/database.py` | SQLAlchemy engine + async session dependency |
| `app/models/models.py` | SQLAlchemy ORM (31+ core classes, 90+ total) |
| `app/models/schemas.py` | Pydantic request/response schemas |
| `app/api/search_router.py` | Public search: `POST /api/search`, `GET /api/search/stats` |
| `app/api/admin_router.py` | Admin CRUD: domains, documents (auto-chunk+embed), tags |
| `app/api/auth_router.py` | JWT login, OAuth2, TOTP 2FA setup |
| `app/api/crud.py` | Database operations layer |
| `app/api/search.py` | Vector similarity + BM25 hybrid search logic |
| `app/utils/embeddings.py` | Text chunking (500 tokens, 50 overlap) + embedding generation |
| `app/utils/auth.py` | JWT signing + bcrypt password hashing |
| `alembic/` | Database migrations (11 schema versions) |
| `scripts/create_admin.py` | Interactive admin user creation |
| `templates/admin.html` | Self-contained admin UI (no external deps) |

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI 0.109+, Pydantic v2, uvicorn
- **Database:** PostgreSQL 13+ (psycopg2-binary 2.9.10), SQLAlchemy 2.0.36
- **Vector Search:** pgvector 0.2.4 (1536-dim vectors, IVFFlat, cosine distance)
- **Cache:** Redis 6+ (Sentinel-managed, persistence enabled)
- **Embeddings:** Voyage AI voyage-large-2 (recommended), OpenAI, Cohere fallback
- **Auth:** python-jose 3.3.0 (JWT/JWE/JWS), passlib + bcrypt 4.1.2
- **Migrations:** Alembic 1.13.1
- **Testing:** pytest 7.4, pytest-asyncio, pytest-cov, 82% coverage, 296 tests

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

## API Groups

| Router | Path | Purpose |
|--------|------|---------|
| Search | `/api/search` | Hybrid semantic + BM25 search |
| Admin | `/admin` | Domain / document / tag CRUD |
| Auth | `/auth` | JWT, OAuth2, TOTP 2FA |
| API Keys | `/admin/api-keys` | Service-to-service key management |
| BugCheck | `/api/bugcheck` | Finding persistence + lifecycle events |
| NeuroForge | `/api/neuroforge` | LLM run logging + inference tracking |
| VibeForge | `/api/vibeforge` | Project sessions + stack analytics |
| AuthorForge | `/api/projects` | Book / chapter / scene management |
| ForgeAgents | `/api/agents-registry` + `/forge-runs` | Agent registry + run evidence |
| Smithy | `/api/v1/smithy` | Planning sessions + portfolio |
| Teams | `/api/teams` | Team management + learning aggregates |
| Events | `/api/events` | Immutable audit log (append-only) |
| Tracing | `/api/tracing` | OpenTelemetry distributed traces |
| Secrets | `/secrets` | LLM API key vault (synced from ForgeCommand) |
| Deployment | `/api-deployment` | Load balancer + instance management |
| Health | `/health` | Liveness probe |

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

## Context Bundle

```bash
./scripts/context-bundle.sh              # Full bundle
./scripts/context-bundle.sh search       # Search / vector focus
./scripts/context-bundle.sh bugcheck     # BugCheck integration
./scripts/context-bundle.sh auth         # Auth + security focus
./scripts/context-bundle.sh schema       # Data models focus
```

Full system documentation: `doc/system/`
