# §15 — Testing

*Last updated: 2026-04-04*

## Current Audited Snapshot

| Metric | Value |
|--------|-------|
| Total test files | `40` |
| Total tests collected | `594` (565 baseline + 29 proving-slice) |
| Inventory command | `PYTHONPATH=. venv/bin/python -m pytest --collect-only -q` |
| Inventory audit date | `2026-04-04` |
| Coverage config | branch coverage enabled in `pytest.ini` |

This section intentionally documents what is currently observable from the repository. It
does not restate historical phase-era coverage claims or assume a full green environment
without PostgreSQL or Redis.

## Current Suite Shape

### API / HTTP Regression

- `tests/test_api/test_admin_endpoints.py`
- `tests/test_api/test_agents_registry_endpoints.py`
- `tests/test_api/test_auth_endpoints.py`
- `tests/test_api/test_health_endpoints.py`
- `tests/test_api/test_press_automation.py`
- `tests/test_api/test_request_timeout_middleware.py`
- `tests/test_api/test_search_endpoints.py`
- `tests/test_api/test_sentinel_endpoints.py`
- `tests/test_api/test_vibeforge_endpoints.py`

### Integration / Workflow

- `tests/test_dataforge_integration.py`
- `tests/test_integration/test_api_endpoints.py`
- `tests/test_integration/test_crud_operations.py`
- `tests/test_integration/test_e2e_workflows.py`
- `tests/test_integration/test_infrastructure_health.py`

### Proving-Slice Intake

- `tests/test_proving_slice_intake.py` — 29 tests covering accepted (8), rejected (5), duplicate/idempotency (3), family gate (3), receipt lookup (4), and adversarial (6). Adversarial tests exercise real contract-core validation without patching. No live DB required (SQLite in-memory via conftest).

### Runtime / Governance / Persistence

- `tests/test_cache_governance.py`
- `tests/test_circuit_breaker.py`
- `tests/test_corpus_governance.py`
- `tests/test_db_replication.py`
- `tests/test_dlq_and_retry.py`
- `tests/test_experience.py`
- `tests/test_policy_envelope_router.py`
- `tests/test_policy_envelope_seed.py`
- `tests/test_rate_limiter.py`
- `tests/test_rate_limits.py`
- `tests/test_runtime_promotion_candidates.py`
- `tests/test_runtime_promotion_execution_worker.py`
- `tests/test_seed_model_catalog.py`
- `tests/test_sql_integration.py`
- `tests/test_token_revocation.py`

### Unit / Security / Load

- `tests/test_security/test_vulnerability_scanning.py`
- `tests/test_unit/test_auth.py`
- `tests/test_unit/test_embeddings.py`
- `tests/test_unit/test_main_startup.py`
- `tests/test_unit/test_models.py`
- `tests/test_unit/test_rate_limit.py`
- `tests/test_unit/test_vibeforge_schemas.py`
- `tests/test_unit/test_vibeforge_services.py`
- `tests/load/test_k6_load.py` (opt-in load surface)

## Running the Suite

### Inventory Only

```bash
PYTHONPATH=. ./.venv/bin/pytest --collect-only -q
```

### Full Repo Suite

```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest -q
```

### With Coverage

```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/pytest --cov=app tests/ --cov-report=term-missing
```

### Focused Governance Surfaces

```bash
.venv/bin/pytest tests/test_policy_envelope_router.py tests/test_runtime_promotion_candidates.py -v
```

## Environment Notes

- Many tests expect a real PostgreSQL database and, for some cases, Redis or pgvector support.
- `tests/load/test_k6_load.py` is opt-in and remains a non-default load surface.
- `tests/test_integration/test_infrastructure_health.py` and other infra-sensitive suites may skip when local dependencies are absent.
- The policy-envelope handlers remain synchronous by design, matching the production app's sync SQLAlchemy usage inside FastAPI.

## `pytest.ini`

The repo root `pytest.ini` is the canonical test configuration surface. It enables:

- `--strict-markers`
- branch coverage reporting
- `asyncio_mode = auto`
- centralized `tests/` discovery

When documenting test totals, prefer the audited collect-only command above over historical
phase summaries.
