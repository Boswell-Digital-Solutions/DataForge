# DataForge Security Audit

**Date:** 2026-06-01
**Auditor:** Claude Code (claude-opus-4-8)
**Branch:** `claude/busy-lamport-h6wXy`
**Scope:** Security-focused audit of the FastAPI service that fronts the Supabase PostgreSQL database. Read-only; no files were modified. Findings were verified against source, not just inferred from documentation.

> **Note on terminology:** This repo is described as the "frontend" of the database. Technically it is a **FastAPI backend service** (DataForge) that acts as the truth-boundary / API gateway in front of a PostgreSQL database hosted on Supabase. The audit treats it as the security-critical access layer to that database.

---

## Summary

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| 1 | 🔴 Critical | `.env` files committed to git, including a real JWT signing key and a real DB password | `.env`, `.env.local`, `.env.production` |
| 2 | 🟠 High | Swagger `/docs` & `/redoc` force-enabled in production, ignoring `ENABLE_SWAGGER_DOCS=false` | `app/main.py:174-175` |
| 3 | 🟠 High | Hardcoded insecure secret fallbacks, gated only by `ENVIRONMENT` string; LLM secrets stored unencrypted when no key | `auth.py:23`, `api_keys.py:108`, `token_rotation.py:99`, `secrets_router.py:56,86` |
| 4 | 🟠 High | No TLS (`sslmode`) enforcement on the remote Supabase connection | `app/database.py:24-37` |
| 5 | 🟡 Medium | CORS `allow_headers=["*"]` combined with `allow_credentials=True` | `app/config.py:107`, `app/main.py:235` |
| 6 | 🟡 Medium | Auth hardening leads (login rate limit, timing enumeration, `X-Forwarded-For` trust) — unverified | `app/api/auth_router.py`, `app/utils/rate_limit.py` |
| — | ✅ Good | `validate_config()` rejects placeholder/default secrets; `render.yaml` keeps Supabase URL & API keys out of repo; `pool_pre_ping` set | — |
| — | ❌ False positive | "SQL injection" in `experience_router.py` — not exploitable | `app/api/experience_router.py:137` |

---

## 🔴 Critical

### 1. `.env` files committed to git (real secrets exposed)

`.env`, `.env.local`, and `.env.production` are **tracked in git** even though `.gitignore` lists `.env` and `.env.local`. They were added in commits `2bdc859` / `7d42d84` and remain in history.

- **`.env`** contains real values:
  - `SECRET_KEY=CX-f…` — the JWT signing secret. Anyone with this can **forge authentication tokens**.
  - `DATAFORGE_DATABASE_URL=postgresql://charlie:ForgeLocal2026xZ@localhost:5432/dataforge` — a real DB username/password (localhost, but the password may be reused elsewhere).
- **`.env.production`** is mostly placeholders (`change-this`, `your-…-here`) → lower risk, but still should not be tracked.
- **Mitigating fact:** the **Supabase** connection string is **not** in the repo. `render.yaml` sets `DATAFORGE_DATABASE_URL` with `sync: false` (Render dashboard only). So the production Supabase database is not directly exposed by the repository.

**Remediation**
1. `git rm --cached .env .env.local .env.production` and commit.
2. Confirm `.gitignore` covers `.env.production` (it currently does not).
3. **Rotate** `SECRET_KEY` (in Render) and the `charlie` / `ForgeLocal2026xZ` DB credential, plus anywhere that password is reused. Rotation is the must-do step — purging git history (BFG / `git filter-repo`) is ideal but rewrites history.

---

## 🟠 High

### 2. Swagger/ReDoc force-enabled in production

`app/main.py:174-175` hardcodes:

```python
docs_url="/docs",
redoc_url="/redoc"
```

`.env.production` sets `ENABLE_SWAGGER_DOCS=false`, `ENABLE_REDOC_DOCS=false`, `ENABLE_OPENAPI_URL=false` — but **nothing reads those flags**. The full API surface of the database gateway (auth, secrets, admin, bugcheck routes) is publicly browsable in production.

**Remediation:** Gate the doc URLs on environment:

```python
_is_prod = os.getenv("ENVIRONMENT", "development") == "production"
app = FastAPI(
    ...,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
```

### 3. Hardcoded insecure secret fallbacks (fail-open)

Four modules fall back to **known constant secrets** when `ENVIRONMENT != "production"`:

| File:Line | Fallback | Risk |
|-----------|----------|------|
| `app/utils/auth.py:23` | `"dataforge-dev-jwt-secret-NOT-FOR-PRODUCTION"` | Forge any JWT |
| `app/auth/api_keys.py:108` | `"dataforge-dev-salt-NOT-FOR-PRODUCTION"` | Predictable API-key hashing |
| `app/auth/token_rotation.py:99` | `"dataforge-dev-token-salt-NOT-FOR-PRODUCTION"` | Predictable admin-token hashing |
| `app/api/secrets_router.py:56` | `"forge-secrets-dev-key-NOT-FOR-PRODUCTION"` | Predictable LLM-secrets encryption |

Additionally, `app/api/secrets_router.py:86` — `_encrypt_secret()` does `return value` (plaintext) when no Fernet key is available, so **LLM provider keys are stored unencrypted** in that path.

The only barrier between "secure" and "all-known-secrets" is the single `ENVIRONMENT=production` string. A typo or a forgotten env var on a new host silently downgrades to known keys.

**Remediation:** Require these secrets explicitly in **all** environments (fail closed / raise on startup). Never persist secrets unencrypted — if no encryption key is configured, refuse the write.

### 4. No TLS enforcement on the Supabase connection

`app/database.py:24-37` (`_build_connect_args`) sets statement/lock/idle timeouts but never sets `sslmode`. For a remote Supabase database, the connection should require TLS. If `DATAFORGE_DATABASE_URL` does not already include `?sslmode=require` (Supabase pooler URLs typically do — **verify yours**), psycopg2 can negotiate a plaintext connection, exposing it to MITM.

✅ `pool_pre_ping=True` is set (`database.py:43`), which correctly handles Supabase's aggressive idle-connection drops.

**Remediation:** For non-sqlite backends, add `"sslmode": "require"` (or `"verify-full"` with the Supabase CA cert) to `connect_args`.

---

## 🟡 Medium

### 5. CORS wildcard headers with credentials

`app/config.py:107` → `CORS_ALLOW_HEADERS = ["*"]`, and `app/main.py:235` → `allow_credentials=True`. Origins **are** restricted by default (`ALLOWED_ORIGINS` defaults to a localhost list), which limits real-world impact. The risk materializes if `ALLOWED_ORIGINS` is ever set to `*` in an environment. Recommend replacing the header wildcard with an explicit list (`Content-Type`, `Authorization`, `X-Correlation-ID`).

### 6. Auth hardening leads (medium confidence — verify before acting)

Surfaced by a sub-agent but **not independently verified** in this audit:
- `/auth/token` login endpoint may lack rate limiting (brute-force exposure).
- `authenticate_user()` returns early when the user is absent vs. running bcrypt when present → timing side channel for username enumeration.
- Rate limiting may trust an unvalidated `X-Forwarded-For` header (spoofable).

Treat these as leads to confirm against `app/api/auth_router.py` and `app/utils/rate_limit.py`, not as confirmed vulnerabilities.

---

## ✅ Done well

- `validate_config()` rejects placeholder `SECRET_KEY` values and the `postgres:postgres` default credential when `ENVIRONMENT=production` (`app/config.py:148,170`).
- `render.yaml` uses `generateValue` for salts/tokens and `sync: false` for the Supabase URL and provider API keys — secrets are not baked into the repo for production.
- Database connection has statement/lock/idle timeouts and `pool_pre_ping`, which is well-suited to Supabase.

## ❌ False positive (excluded)

A sub-agent flagged "Critical SQL injection" at `app/api/experience_router.py:137`. **Verified not exploitable:** the `WHERE` clause is assembled only from fixed literal strings (`"agent_archetype = :archetype"`, `"outcome = :outcome"`) with bound parameters, and `query_embedding` is typed `list[float]` (`app/models/agentic_reasoning_schemas.py:82`), so interpolated values are numeric. The string-building *pattern* is fragile and worth refactoring to the ORM, but there is no injection.

---

## Recommended order of action

1. **Now:** Untrack the `.env` files and rotate the `SECRET_KEY` and DB password (Finding 1).
2. **Next:** Gate `/docs` in production (Finding 2) and make secrets fail-closed (Finding 3).
3. **Then:** Enforce DB TLS and tighten CORS (Findings 4–5).
4. **Verify:** The auth-hardening leads (Finding 6).
