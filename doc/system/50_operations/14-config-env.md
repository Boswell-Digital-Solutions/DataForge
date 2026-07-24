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
| `DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED` | bool | `false` | NO | Fail-closed canonical telemetry writer switch. Enable only after migration `20260723_01` and producer key bindings are verified |
| `DATAFORGE_TELEMETRY_BASE_URL` | URL | unset | For emission | Explicit canonical DataForge ingest origin; no deployment-URL inference |
| `DATAFORGE_TELEMETRY_API_KEY` | secret | unset | For emission | Dedicated `telemetry:write` key bound to `service_name=dataforge`, exact `ENVIRONMENT`, and `tenant_ref=null`; never falls back to `DATAFORGE_API_KEY` |
| `DATAFORGE_TELEMETRY_TIMEOUT` | float seconds | `5` | NO | Positive finite canonical transport timeout |

**Example:**
```
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
REDIS_URL=redis://localhost:6379/0
DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=false
DATAFORGE_TELEMETRY_BASE_URL=http://127.0.0.1:8000
DATAFORGE_TELEMETRY_API_KEY=
DATAFORGE_TELEMETRY_TIMEOUT=5
```

Never use SQLite in production. The pgvector extension requires PostgreSQL 13+.

`DataForge` no longer treats pgvector startup init as a fatal boot dependency. If the database is temporarily unavailable during startup, the service still boots, `/health` stays live, and `/ready` reports the database/pgvector failure until connectivity recovers.

The ForgeEvent.v1 route is mounted while the writer switch is disabled so
operators can authenticate against the capability endpoint and observe
`write_enabled: false`. Set the switch to `true` only after the canonical
migration and every producer key's `service_name`, `environment`, `tenant_ref`,
and `telemetry:write` metadata have been verified. Setting it back to `false`
stops new writes without deleting stored evidence.

The writer switch controls the sink; the three `DATAFORGE_TELEMETRY_*`
variables control DataForge's own search producer. Keep the producer key unset
until the migration, writer switch, capability identity, and exact key binding
are proved together. A missing or invalid producer configuration fails
telemetry closed without failing the search request. The producer never reuses
the service's broad DataForge API key.

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

## Render Build Authentication

| Variable | Required on Render | Notes |
|----------|--------------------|-------|
| `FORGE_TELEMETRY_TOKEN` | YES | Preferred build-only GitHub token with `Contents:Read` on the pinned `forge-telemetry` and `forge_contract_core` repositories |
| `GITHUB_TOKEN` | Fallback | Accepted only when `FORGE_TELEMETRY_TOKEN` is absent |

The build uses HTTPS token rewriting in `scripts/render-git-auth.sh`; it does not consume
`SSH_KEY` or `SSH_KEY_B64`. Never print either token. The web build is the sole Render migration
runner. The cron build verifies exactly one Alembic head and its runtime preflight verifies the
`supabase_log_events` table, but the cron does not run migrations concurrently.

## Supabase Log Poller

| Variable | Required for cron | Notes |
|----------|-------------------|-------|
| `DATAFORGE_DATABASE_URL` | YES | Same migrated PostgreSQL authority as the web service |
| `SUPABASE_PROJECT_REF` | YES | Lowercase Supabase project reference |
| `SUPABASE_ACCESS_TOKEN` | YES | Management API PAT/OAuth token with analytics-log read permission |
| `SUPABASE_LOG_IDENTITY_SALT` | Recommended | One-way identity hashing; raw identity is dropped when absent |
| `SUPABASE_LOG_SOURCE_TABLE` | NO | Fixed allow-listed source; default `edge_logs` |
| `SUPABASE_LOG_POLL_LOOKBACK_SECONDS` | NO | Empty-table lookback; must be 1–86,340 seconds |
| `SUPABASE_LOG_POLL_OVERLAP_SECONDS` | NO | Cursor overlap for safe retry/deduplication |
| `SUPABASE_LOG_POLL_MAX_ROWS` | NO | Per-poll cap; must be 1–10,000 |

The configured token needs the `analytics:read` OAuth scope or
`analytics_logs_read` fine-grained permission. The poller uses Supabase's current unified logs
endpoint and ClickHouse SQL; do not revert it to the deprecated `logs.all` endpoint.

Operational failures appear only as `poller_failed category=<category> code=<code>`. Diagnose
using those values and variable *names*; do not paste token values or raw upstream bodies.

## AuthorForge Analytics Writer

`API_KEY_SALT` is required for the database-backed API key system in production. Create a
dedicated AuthorForge key whose metadata contains `service: authorforge` and whose `scopes`
array contains `analytics:write`. Do not reuse a general-purpose event/admin key. There are no
environment variables for AuthorForge content sync because content sync is prohibited.

---

## Full `.env.example` Reference

```dotenv
# Database
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=<generate-with-secrets.token_hex-32>
JWT_SECRET_KEY=<same-as-SECRET_KEY>
API_KEY_SALT=<generate-long-random-value>
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

# Render build-only private dependency auth
FORGE_TELEMETRY_TOKEN=<github-fine-grained-read-token>

# Supabase log cron only
SUPABASE_PROJECT_REF=<project-ref>
SUPABASE_ACCESS_TOKEN=<management-api-token>
SUPABASE_LOG_IDENTITY_SALT=<generate-long-random-value>
SUPABASE_LOG_SOURCE_TABLE=edge_logs

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
