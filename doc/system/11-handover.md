# §11 — Handover, Critical Constraints & Migration Runbook

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
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8788 --reload
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
- [ ] Prometheus scrape job configured for `/metrics`
- [ ] Grafana dashboards imported
- [ ] Backup schedule confirmed (daily/weekly/monthly + PITR)

If Postgres or the pgvector extension is unreachable during a deploy, `DataForge` should still boot and bind a port. Treat `/ready` as the authoritative signal for database/pgvector availability; do not revert to a startup path that exits the worker before `/health` can respond.
- [ ] `alembic upgrade head` run against production DB before traffic cutover
- [ ] Smoke test: `GET /health`, `GET /ready`, `POST /auth/login`, `POST /api/search`

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

Monitor Redis memory usage. The cache TTLs in the `/cache` router should be tuned based on actual usage patterns. If Redis memory exceeds 80% of limit, reduce TTLs or increase memory allocation.

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `/home/charlie/Forge/ecosystem/DataForge/app/main.py` | FastAPI app, router registration, lifespan |
| `/home/charlie/Forge/ecosystem/DataForge/app/database.py` | SQLAlchemy engine, session factory |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/models.py` | All ORM models (31+ classes) |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/schemas.py` | All Pydantic schemas (90+) |
| `/home/charlie/Forge/ecosystem/DataForge/app/api/crud.py` | Database operations |
| `/home/charlie/Forge/ecosystem/DataForge/app/api/search.py` | Hybrid search implementation |
| `/home/charlie/Forge/ecosystem/DataForge/app/utils/embeddings.py` | Chunking + embedding generation |
| `/home/charlie/Forge/ecosystem/DataForge/app/utils/auth.py` | JWT + bcrypt utilities |
| `/home/charlie/Forge/ecosystem/DataForge/alembic/versions/` | Migration history |
| `/home/charlie/Forge/ecosystem/DataForge/tests/` | 32 test files |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/multi_provider_models.py` | Multi-provider pipeline models (6 tables) |
| `/home/charlie/Forge/ecosystem/DataForge/app/models/sentinel_models.py` | Sentinel health + healing models |
| `/home/charlie/Forge/ecosystem/DataForge/app/api/sentinel_router.py` | Sentinel sweep + healing REST API |
| `/home/charlie/Forge/ecosystem/DataForge/scripts/seed_model_catalog.py` | Canonical model catalog seed script; retires stale xAI aliases |
| `/home/charlie/Forge/ecosystem/DataForge/.env.example` | All env vars documented |
| `/home/charlie/Forge/ecosystem/DataForge/requirements.txt` | Pinned dependencies |

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

*BDS Documentation Protocol v1.0 — Last updated: 2026-02-18*
