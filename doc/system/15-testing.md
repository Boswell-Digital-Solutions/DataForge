# §15 — Testing

## Cloud-Image Durable State Gate

Run the focused SQLite contract/rollback suite and the PostgreSQL concurrency
gate separately:

```bash
scripts/run-tests-isolated.sh -- -q \
  tests/test_cloud_image_state.py tests/test_cloud_image_recovery.py
scripts/run-tests-isolated.sh --no-postgres -- -q tests/test_cloud_image_state.py   # SQLite only, no container
scripts/run-tests-isolated.sh -- -q tests/test_cloud_image_state_postgres.py       # the runner supplies the disposable PostgreSQL
```

Migration proof covers a clean `alembic upgrade head`, an upgrade from stamped
revision `20260906_01`, `alembic current` at `20260913_02`, and a downgrade and
re-upgrade across `20260913_01`. The recovery suite covers lease replay,
renewal, release, expiration/takeover, stale fencing, attempt reconciliation and
ordering, atomic attempt/transition linkage, outbox retry/reclaim/ack fencing,
and injected rollback boundaries. The two PostgreSQL cases prove single-winner
job transitions, worker leases, and outbox claims. They skip unless the explicit
test URL is supplied; SQLite cannot prove row-lock concurrency or
`SKIP LOCKED` behavior.

*Last updated: 2026-07-25*

## Current Audited Snapshot

| Metric | Value |
|--------|-------|
| Total test files | `59` |
| Total tests collected | `791` |
| Inventory command | `scripts/run-tests-isolated.sh -- --collect-only -q --no-cov` |
| Inventory audit date | `2026-07-24` |
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

### Production Boundary Regression

- `tests/test_unit/test_supabase_log_poller.py` — config/API/database failure categories,
  bounded query windows, redaction, and idempotent retry.
- `tests/test_unit/test_supabase_log_ingest.py` — allow-listing, sensitive-field removal, and
  identity pseudonymization.
- `tests/test_unit/test_authorforge_analytics.py` — strict envelope allow-list, size/cardinality
  bounds, content/identity rejection, content-bound idempotency in the dedicated analytics
  store, generic rejection responses, and mounted-route inventory.
- `tests/test_unit/test_authorforge_boundary_audit.py` — synthetic proof that the read-only audit
  reports IDs/counts/categories without reading or outputting content fields.

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
- `tests/test_telemetry_incidents.py` — CP6 derivation, source-hash proof,
  idempotency/deduplication, exact producer/reader binding, restricted
  projection, kill switches, route inventory, and corrupt-authority rejection.

The CP6 PostgreSQL proof is
`scripts/prove_telemetry_cp6_postgres.sh`. It verifies migration
`20260725_03`, least-privilege grants/RLS, hard false action constraints,
backup/restore, evidence-retaining downgrade, and re-upgrade.

The RFC-FT-04 candidate proof is
`scripts/prove_rfc_ft_04_candidate_postgres.sh` (run through `pg_virtualenv`).
It is admission-proof evidence only; `ForgeAIInferenceSemantics.v1` is not
admitted. It drives the real HTTP route with a synthetic API key minted in the
throwaway cluster and a throwaway login role in `dataforge_telemetry_ingest`.
It proves: authentication and subject binding still run first; ordinary
runtime rejects every candidate event and stores nothing; with the candidate
admitted only through a dependency override in the proof process, each invalid
fixture is rejected with its code and no row, each valid fixture is `inserted`
then `exact_replay` with the authority's digest and exact JSONB storage, and
same-ID/different-content is `409 event_identity_conflict`; a missing
validator returns `503` and stores nothing. The fixtures and the vendored
validator are byte-for-byte copies from forge_contract_core.

`tests/test_forge_event_profile_enforcement.py` covers the same boundary
through `TestClient` on the SQLite harness, plus validator pinning, drifted
bytes, validator faults, malformed measurement classes, and value-free errors.

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

## Isolated Test Runner

Status: implementation in review. Finding M1 stays open until a separately authorized closure proof.
The design is `docs/proposals/M1_TEST_ISOLATION_REPAIR_DESIGN.md`. The tracked finding is in `docs/KNOWN_ISSUES.md`.

Every run of the suite must use `scripts/run-tests-isolated.sh`.
A run of `pytest` without the runner exits with code 87 before `tests/conftest.py` imports `app`.
No override exists. The refusal also covers `--collect-only`.

```bash
scripts/run-tests-isolated.sh -- tests/ -q                       # the suite, SQLite
scripts/run-tests-isolated.sh --database postgres --migrate -- tests/ -q   # the suite, disposable PostgreSQL
scripts/run-tests-isolated.sh --canary                           # the canary suite of the runner (in the sandbox)
python -m pytest tests/isolation/canary/host -c pytest.ini -o addopts= -o python_files='check_*.py' \
  --confcutdir tests/isolation/canary/host -p no:cacheprovider    # the host canaries of the runner
```

### What the runner does

The runner starts the tests in a new user, network, pid and mount namespace.
The namespace has no route out. It has a loopback interface only.
The mount namespace starts from an empty root. It binds in only the files that the tests need.
The sockets of the host (`/run`, `/var/run`, the Docker socket) do not exist inside it.
A seccomp filter allows `socket()` for `AF_UNIX`, `AF_INET` and `AF_INET6` only.
The filter also denies the x32 ABI and `io_uring_setup`, `io_uring_enter` and `io_uring_register`.
The filter covers `x86_64` only. On another architecture the runner exits 86.
The digest of the filter is pinned in `scripts/isolated_test_runner.py`.

Two routes create the namespaces. The runner tries `bwrap` first. It tries `unshare -rnmpf --propagation private` second.
No route uses `sudo`. If neither route works, the runner exits 86. Docker `--internal` is a documented fallback only.
The test process never runs as real root. It has no capability, and `NoNewPrivs` is 1.

A guard installs at interpreter start (`tests/isolation/sitecustomize.py`).
The guard checks every connection, name lookup, spawned program and PostgreSQL target against a manifest.
A violation is a `BaseException`. The guard also appends it to `violations.jsonl`.
The runner reads that file after pytest exits. One line fails the run with code 87.
A pytest plugin converts a skipped or passed test that caused a violation into a failed test.

### Local services

| Service | How the runner provides it |
|---|---|
| PostgreSQL with pgvector | The pinned local image `pgvector/pgvector:pg16`, started with `--pull=never --network none`. A Unix socket directory is the only door. |
| NeuroForge | A stub on a loopback port that the runner chooses. The embedding tests run against it. |
| Redis | Declared absent. A probe is logged. Tests that use `_get_redis_or_skip` skip before any connection, with a declared reason. |

The runner never pulls an image. A missing image is exit 86.
The CI workflow pulls the image by digest in a separate step.
The runner sets every URL and DSN. It ignores ambient variables and removes every proxy variable.
The runner refuses to start when a `.env` file exists in the repository or a parent directory.

### No secret exists

The runner starts PostgreSQL with `POSTGRES_HOST_AUTH_METHOD=trust` and the explicit role `dftest`. No password exists.
This is a recorded deviation from the design, which said "random credentials".
The reason is that a password would have to reach the sandbox through a file, and a file with a secret is a clear-text store.
The protection is as follows.
The container has `--network none`, so the socket is the only door.
The run directory has mode 0700.
The marker table checks the identity of the server.
The manifest of the guard allows only that socket.
The DSNs name the role and the socket directory. They hold no password.
A canary scans the run files for secret-like values.

### CI provider option A

The design lets the runner create the namespaces without privilege and probe first.
The first CI run proved the fail-closed exit 86 on a hosted runner. No test started.
The run is https://github.com/Boswell-Digital-Solutions/DataForge/actions/runs/37258223856.
The ubuntu 24.04 runner sets `kernel.apparmor_restrict_unprivileged_userns=1`, which blocks both routes.
The workflow step "Allow unprivileged user namespaces on the runner VM" sets that key to 0 before the runner step.
It also sets `kernel.unprivileged_userns_clone=1` where the key exists, and it prints the values before and after.
The step changes the setting of the ephemeral runner VM only.
The tests still run as the unprivileged runner user inside the sandbox.
The `sudo` route for running tests stays refused.
The runner still probes, and it exits 86 if the namespaces stay blocked.
If loopback in `bwrap` still fails after the step, the fallback is Docker `--internal` (design option B). It is not implemented.

### Render build and preflight

`scripts/render-build.sh` calls `scripts/preflight.sh --no-tests`.
The flag skips the two pytest phases and keeps every other check (dependencies, single Alembic head).
Render has no `bwrap` and no Docker, so the runner cannot isolate there.
Nothing is live, and CI runs the suite under the runner.
The flag is the only mode that skips the tests. No option runs the suite without the runner.

### Closure evidence tool

`python scripts/prove_planted_violation.py` plants a temporary test file in `tests/`.
It holds a connect to `192.0.2.1` and a lookup of `x.invalid`. Each is wrapped in `except Exception: pytest.skip(...)`.
It runs only that file through the runner, with the real `tests/conftest.py`.
It expects exit 87, two failed tests and two recorded violations. It removes the file in every case.
This tool is one step of the closure evidence. It does not close M1.

### Exit codes

| Code | Meaning |
|---|---|
| 86 | A precondition failed. No test started. |
| 87 | A violation, a refused run, or a skip with no declared reason. |
| 88 | A service did not stop in teardown. |
| other | The normal pytest status. |

After exit 86, 87 or 88 the runner keeps its run directory `/tmp/dfi-<run id>` for evidence.
After exit 0 it removes the directory.
Remove a kept directory by hand when you no longer need it.
A kept `pg` subdirectory can hold files that belong to uid 999. Run `docker rm --force dfiso-pg-<run id>` first, then remove the directory.

The runner refuses a Docker client that does not use a local Unix socket.
It refuses a remote `DOCKER_HOST` or a remote Docker context with exit 86.
It starts the container with an explicit environment, and it always removes the container by its fixed name.
The sandbox gets `/dev/null` as standard input. It inherits no socket.

A skip has a declared reason only when its text equals, character for character, an entry of `DECLARED_SKIPS` in `scripts/isolated_test_runner.py`.
The declared Redis reason is built from the manifest. No pattern or prefix match exists.
The runner prints every undeclared skip, with its test id and exact reason, on stderr and in the `--report` JSON.
The report lists every skip.

Declared skips and why (the local full run: 1050 passed, 23 skipped, 0 violations):

| Skips | Reason | Why it is declared |
|---|---|---|
| 9, `test_infrastructure_health.py` Redis tests | `declared absent: redis (...)` | The decision owner declared Redis absent. |
| 3, `tests/test_experience.py` | `Requires pgvector ...` | A hard-coded `@pytest.mark.skip`. It is unrelated to the sandbox. |
| 3, `tests/load/test_k6_load.py` | `Load tests require an explicit RUN_LOAD_TESTS=1 opt-in ...` | An opt-in load surface. It needs a live API server. |
| 8, `test_infrastructure_health.py` database and driver tests | Three SQLite reasons (five tests share the first one) and `psycopg not installed` | See the note below. |

The eight infrastructure tests skip although the runner provides PostgreSQL.
The cause is not the runner. The `db` fixture of `tests/conftest.py` is a fixed in-memory SQLite engine, and it ignores `DATAFORGE_DATABASE_URL`.
These checks never ran on any backend, before or after the runner. This is a coverage gap that exists without the runner.
A later change can give those tests a PostgreSQL fixture. `test_psycopg_available` imports psycopg 3, but `requirements.txt` pins psycopg2 only.

### Canaries

The canaries use only RFC 5737 addresses (`192.0.2.0/24`) and `.invalid` names.
They do not import `app` and do not run the suite.
The sandbox canaries are in `tests/isolation/canary/sandbox`. The host canaries are in `tests/isolation/canary/host`.
The default `pytest` run does not collect them, because their files do not match `python_files`.

### Threat model

The guard and the plugin are in-process Python. They are defence in depth against accidental calls. They do not stop a hostile test process.
The kernel layers are the barrier: the network namespace, the mount allow-list, the seccomp filter and the absence of inherited sockets.
A hostile test can truncate `violations.jsonl` or silence the stderr marker.
That can erase only the record of an attempt that the kernel already blocked.
A hardening option is a write-only pipe that the runner drains.
The PostgreSQL container runs with `--cap-drop ALL`, plus only the five capabilities that its entrypoint needs, and with `no-new-privileges`.
After a run, a throwaway container of the same pinned image removes every file in the socket directory, so uid 999 residue does not keep the run directory.

### Known limits

- A Python child that starts with a socket as its standard input exits 87. The inherited-descriptor check of the guard causes this.
- The runner limits `DOCKER_HOST` to `unix://`. A local `docker.sock` that forwards to a remote TCP host is not detected.
- The guard cannot see raw C calls (`ctypes`). The namespaces and the seccomp filter cover them.
- The runner has no proof for a full run of the suite. Closure of M1 needs that proof.
- `scripts/preflight.sh`, `run_tests.sh`, `ci_gate.sh` and the `make test` target now call the runner.
- The `Makefile` on `master` has literal `\t` characters instead of tabs, so `make` fails with "missing separator". This is older than the runner.
- Skip reasons are global. They are not bound to a (file, reason) pair, so the same text in another file is also declared.
- The two long SQLAlchemy skip reasons contain version-sensitive text. A SQLAlchemy upgrade can change them, and the run then fails closed with exit 87.
- `app/tests/` has no gate. The owner decision on it is pending. A direct `pytest app/tests` is not refused and not guarded.

## Running the Suite

Every command below must run through the runner (see Isolated Test Runner). Direct `pytest` exits 87.

### Inventory Only

```bash
scripts/run-tests-isolated.sh -- --collect-only -q --no-cov
```

### Full Repo Suite

```bash
scripts/run-tests-isolated.sh --database postgres --migrate -- -q
```

### With Coverage

```bash
scripts/run-tests-isolated.sh --database postgres --migrate -- --cov=app tests/ --cov-report=term-missing
```

### Focused Governance Surfaces

```bash
scripts/run-tests-isolated.sh -- tests/test_policy_envelope_router.py tests/test_runtime_promotion_candidates.py -v
```

### Focused Poller and AuthorForge Boundary

```bash
scripts/run-tests-isolated.sh -- \
  tests/test_unit/test_supabase_log_ingest.py \
  tests/test_unit/test_supabase_log_poller.py \
  tests/test_unit/test_authorforge_analytics.py \
  tests/test_unit/test_authorforge_boundary_audit.py -q
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

## Which CI runs for which change

A change that touches only documentation runs the Documentation CI and no code CI.
A change that touches any other file runs the code CI.
A change that touches both runs both.
No scheduled run is added for the code CI.
When the scope is unknown, the code CI runs.

Documentation means `docs/**`, `doc/**` and any `*.md` file.
A change to `.github/workflows/**` is code.

| Workflow | Class | Documentation-only change |
|---|---|---|
| `documentation.yml` | Documentation CI | Runs. It builds `doc/system` and fails on a difference in `doc/`. |
| `test.yml` | Code CI | Does not start. A `paths` filter on `push` and `pull_request` excludes documentation. |
| `docker.yml` | Code CI | Does not start for a branch push or a pull request. A tag push (`v*`) always runs. |
| `security.yml` | Security scan | The `secrets` job runs. Bandit, Safety, OWASP and CodeQL skip. |
| `deploy.yml` | Release | No change. It starts only for a `release-*` tag or by hand. |

The filter in `test.yml` and `docker.yml` is:

```yaml
paths:
  - '**'
  - '!docs/**'
  - '!doc/**'
  - '!**/*.md'
  - 'docs/plans/DFG_GOV_01/**'
  - 'docs/archive/TELEMETRY_INTEGRATION_STATUS.md'
```

The last matching pattern wins, so the re-includes come last.
Documentation that a test reads is code. Two paths are re-included:

- `docs/plans/DFG_GOV_01/**`. `tests/test_dfg_gov_01.py` loads the JSON fixtures in this directory.
- `docs/archive/TELEMETRY_INTEGRATION_STATUS.md`. `tests/test_dataforge_telemetry_caller.py`
  asserts that this file does not exist.

The `.dockerignore` file already excludes `docs/` and the root `*.md` files from the image.
No run-time code reads `doc/` or any `*.md` file.
The service reads `service_contract.v1.json`. That file is not documentation and always runs the code CI.

Security scans run on every change. A documentation file can hold a leaked secret.
A `paths` filter cannot keep one job of a workflow running, so `security.yml` has no filter.
The `scope` job runs `scripts/ci-change-scope.sh`. The script prints `code=false` only when
every changed file is documentation. The scan jobs run unless the output is `code=false`.
An empty list, a failed scope job and the weekly schedule all run the scans.
`scripts/ci-change-scope.sh` keeps the same re-include list as the `paths` filter.
`tests/test_ci_change_scope.py` tests the script.

Render builds follow the same rule. `buildFilter.ignoredPaths` in `render.yaml` skips a build for a documentation-only push.
Render ignores a path over any include rule, so the two re-included paths above are not in that list.

Do not add a required check on a path-filtered workflow. The check stays pending, and the merge blocks.
Do not rename a job to a name that a rule requires. Add a re-include for each new documentation path that code reads.
