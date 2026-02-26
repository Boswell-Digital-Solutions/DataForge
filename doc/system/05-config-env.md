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

**Provider fallback order:** Voyage AI → OpenAI → Cohere

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

## NeuroForge Integration

These fields are defined in `app/neuroforge/config.py` (`NeuroForgeSettings`) and control the DataForgeClient's resilience behavior when calling NeuroForge.

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `NEUROFORGE_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS` | int | `1` | Max trial calls allowed in half-open state |
| `NEUROFORGE_RETRY_MAX_ATTEMPTS` | int | `3` | Max retry attempts for transient failures |
| `NEUROFORGE_RETRY_INITIAL_DELAY` | float | `0.5` | Initial retry delay in seconds |
| `NEUROFORGE_RETRY_BACKOFF_BASE` | float | `2.0` | Exponential backoff base multiplier |

These complement the existing `NeuroForgeSettings` fields (`NEUROFORGE_BASE_URL`, `NEUROFORGE_TIMEOUT`, circuit breaker thresholds).

---

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
