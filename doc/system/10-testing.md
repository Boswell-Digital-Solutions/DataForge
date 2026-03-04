# §10 — Testing

## Overview

| Metric | Value |
|--------|-------|
| Total test files | 31 |
| Total tests collected | 529 |
| Latest verified result | 513 passed, 16 skipped |
| Coverage config | branch coverage enabled via `pytest.ini` |

## Test Pyramid

### Unit Tests

Target individual functions and classes with no database or network I/O. Use `pytest-mock` for dependency injection.

| Test File | Coverage Area |
|-----------|--------------|
| `test_auth.py` | JWT creation, validation, expiry, bcrypt hashing |
| `test_encryption.py` | Fernet field encryption/decryption, key rotation |
| `test_rate_limiting.py` | Token bucket logic, window reset, burst handling |
| `test_anomaly_detection.py` | All 6 detection types, threshold boundaries |
| `test_embeddings.py` | Chunking logic, overlap correctness, truncation |
| `test_rrf.py` | Reciprocal rank fusion merge correctness |
| `test_fingerprint.py` | Fingerprint stability across equivalent inputs |
| `test_lifecycle.py` | State machine transitions (valid + invalid) |
| `test_schemas.py` | Pydantic schema validation, edge cases |

### Integration Tests

Require live PostgreSQL and Redis connections. Run against a test database (separate from dev). Use fixtures to set up and tear down state.

| Test File | Coverage Area |
|-----------|--------------|
| `test_search_integration.py` | Full hybrid search pipeline end-to-end |
| `test_admin_api.py` | Document CRUD + auto-chunking trigger |
| `test_neuroforge_api.py` | NeuroForge router: run logging, inference, context |
| `test_vibeforge_api.py` | VibeForge router: projects, sessions, outcomes |
| `test_authorforge_api.py` | AuthorForge V2: full content hierarchy |
| `test_bugcheck_api.py` | BugCheck router: finding ingestion, lifecycle |
| `test_bugcheck_access_control.py` | Scope enforcement, invalid token types |
| `test_teams_api.py` | Team management, member RBAC |
| `test_agents_registry.py` | Agent registration and retrieval |
| `test_smithy_api.py` | Planning sessions, portfolio, evaluations |
| `test_cache_failover.py` | Redis sentinel failover simulation |
| `test_db_failover.py` | PostgreSQL replica failover simulation |
| `test_dlq.py` | Dead letter queue write + replay |

### Security Tests

| Test File | Coverage Area |
|-----------|--------------|
| `test_auth_security.py` | OAuth2 flows, TOTP 2FA, backup codes |
| `test_jwt_security.py` | Token forgery, expiry bypass, algorithm confusion |
| `test_run_token.py` | run_token scope enforcement, nonce replay protection |
| `test_api_key_security.py` | Key revocation, scope isolation |

### Compliance Tests

| Test File | Coverage Area |
|-----------|--------------|
| `test_compliance_gdpr.py` | Erasure flow, soft delete, hard delete scheduling |
| `test_compliance_encryption.py` | PII field encryption in stored records |
| `test_audit_log.py` | HMAC integrity, append-only enforcement |

### E2E Tests

Full workflow tests that exercise multiple routers in sequence, simulating real service interactions.

| Test File | Coverage Area |
|-----------|--------------|
| `test_e2e_bugcheck_run.py` | Full BugCheck run: create → findings → lifecycle → finalize |
| `test_e2e_neuroforge_workflow.py` | LLM run → results → performance → context retrieval |
| `test_e2e_authorforge_project.py` | Book → chapters → scenes → manuscript compilation |

## Running Tests

### All Tests
```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest -q
```

### With Coverage
```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest --cov=app tests/ --cov-report=term-missing
```

### Specific Domain
```bash
pytest tests/test_bugcheck_api.py -v
pytest tests/test_bugcheck_access_control.py -v
```

### Security Tests Only
```bash
pytest tests/test_auth_security.py tests/test_run_token.py tests/test_jwt_security.py -v
```

### Compliance Tests Only
```bash
pytest tests/test_compliance_gdpr.py tests/test_audit_log.py -v
```

## Test Configuration

`pytest.ini` at repository root:

```ini
[pytest]
testpaths = tests
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-branch
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (database required)
    infrastructure: Infrastructure and connectivity tests
    slow: Slow tests
    auth: Authentication tests
    search: Search functionality tests
    admin: Admin API tests
    embeddings: Embedding generation tests
    security: Security and vulnerability tests
    load: Load testing
    e2e: End-to-end workflow tests
asyncio_mode = auto
```

### Test Database Setup

Integration tests require a separate PostgreSQL database:

```bash
# Create test database
createdb dataforge_test

# Run migrations against test DB
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge_test \
  alembic upgrade head

# Run integration tests
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge_test \
  pytest tests/ -m integration -v
```

The live validation run on 2026-03-01 used Supabase Postgres for the database-backed suite.
Some tests still skip by design when optional infrastructure is absent (for example, pgvector-
specific raw SQL tests on SQLite fixtures, k6 load tests unless `RUN_LOAD_TESTS=1`, and local
NeuroForge-dependent infrastructure checks).

The policy envelope router tests call the handler functions directly with a real SQLAlchemy
session fixture. Those handlers are intentionally synchronous, matching the production FastAPI
configuration that runs sync ORM work in a threadpool instead of on the event loop.

### Fixtures

Key fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def db_session():
    """Provides a rollback-isolated database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """FastAPI test client with overridden database dependency."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token(client):
    """Creates an admin user and returns a valid JWT."""
    # ... creates user, logs in, returns token

@pytest.fixture
def run_token():
    """Returns a valid scoped run_token for test run."""
    # ... generates run_token with test run_id
```

## Latest Validation Snapshot

Validated on 2026-03-01:

- `alembic upgrade head` passed
- `alembic downgrade -1` passed
- `alembic upgrade head` passed again
- `pytest -q --maxfail=1` completed with `513 passed, 16 skipped`

Skipped tests in that run were environmental, not failing assertions:

- `tests/test_experience.py` requires real `pgvector` for raw `<=>` SQL coverage
- `tests/load/test_k6_load.py` is opt-in and requires `RUN_LOAD_TESTS=1`
- `tests/test_integration/test_infrastructure_health.py` skips PostgreSQL-only or NeuroForge-only checks when those dependencies are not present

## Coverage Targets

| Area | Current | Target |
|------|---------|--------|
| Overall | 82% | 85%+ |
| Auth module | 95% | 95%+ |
| BugCheck router | 90% | 90%+ |
| Lifecycle state machine | 100% | 100% |
| Search engine | 88% | 88%+ |
| Encryption utilities | 92% | 92%+ |
| Admin router | 78% | 85%+ |
| Domain-specific routers | 74% | 80%+ |

Lines currently not covered: error recovery branches in database failover simulation, some OAuth2 provider edge cases, and k6 load test infrastructure.

## Preflight Script (`scripts/preflight.sh`)

A single deterministic gate script that validates the service before deployment. If preflight passes locally, Render will pass.

```bash
bash scripts/preflight.sh
```

### Phases

| Phase | Check | Blocking |
|-------|-------|----------|
| 1 | `pip install -r requirements.txt` | Yes |
| 2 | Alembic heads (single head required) | Yes |
| 3 | `pytest` (unit tests, `-x` fail-fast) | Yes |

### Test Exclusions

Preflight runs only tests that work without live infrastructure. The following directories are excluded because they require PostgreSQL, Redis, pgvector, or a running server:

| Excluded Path | Reason |
|---------------|--------|
| `tests/test_integration/` | Full integration tests (live DB) |
| `tests/test_api/` | API endpoint tests (`db_session` fixture) |
| `tests/test_unit/` | Unit tests that import DB fixtures |
| `tests/test_sql_integration.py` | Raw SQL queries against PostgreSQL |
| `tests/test_performance_optimization.py` | Performance benchmarks (live DB) |
| `tests/test_security/` | Security tests (live DB + Redis) |
| `tests/load/` | k6 load tests (running server) |

### Preflight Results (Mar 2026)

| Metric | Value |
|--------|-------|
| Tests collected | 174 |
| Passed | 171 |
| Skipped | 3 |
| Duration | ~12 seconds |

### Venv Auto-Detection

The script automatically activates `.venv` or `venv` if present and no virtual environment is already active. On Render, dependencies are pre-installed by the build command.

---

## Load Testing (Optional)

k6 scripts are available for load testing but are not part of the standard CI pipeline:

```bash
# Install k6
# Run against local instance
k6 run scripts/load_test_search.js
k6 run scripts/load_test_ingestion.js
```

Target: sustain 1,000 RPS at p95 < 100ms with a test corpus of 100,000 chunks.
