# Known Issues

This document tracks confirmed issues and concerns awaiting investigation. Blocking impact and verification status are stated per item.

## The Runtime-Promotion Candidate Tables Are Missing From The Connected Database (2026-10-05)

- **Location**: Database project `DataForgedb` (ref `embvfponjxejbtrkryzs`). Migrations
  `75660723bef6` (candidates) and `20260401_1200` (candidate decisions).
- **Status**: Open. No repair applied. Not authorized.
- **What is wrong**: At 2026-10-05 10:02 UTC a read-only catalog query found no relation named
  `runtime_promotion_candidates` or `runtime_promotion_candidate_decisions` in any schema.
  `public.alembic_version` holds one revision, `20260930_01`. The version record says head, but the
  tables do not exist.
- **Source**: A read-only diagnostic by GPT Pro on 2026-10-05, using the Render and Supabase connectors. A
  Claude Code session did not run the queries. It checked the repository claims only: both migration files exist
  at commit `65c0e773`, `20260930_01` is a migration revision, and `20260711_01` names project
  `embvfponjxejbtrkryzs` as DataForgedb. The database and log results are unverified by this session.
- **Evidence**: Render logs for service `srv-d503rdvpm1nc73c3t8pg` show
  `psycopg2.errors.UndefinedTable: relation "runtime_promotion_candidates" does not exist` for
  `GET /api/v1/runtime-promotion/candidates` (2026-09-30 10:49 UTC) and for the detail route (10:56 UTC).
  This is the cause of the HTTP 500 that Forge_Command recorded as FC-RT-20260930-010.
- **Live target confirmed 2026-10-05**: Charlie ran a read-only shell check on Render. Data Forge resolves its
  database to project `embvfponjxejbtrkryzs`, database `postgres`, with no target overrides. This is the inspected
  database. The missing tables are a live schema-drift fault, not a connection-target mistake.
- **Not established**: Why the tables are missing. Whether they held data. Whether the other four runtime-promotion
  tables exist (the diagnostic checked two). Whether an authenticated call works now. The read-only check used
  the connector role, not the application role.
- **Audit 2026-10-05 (GPT Pro, read-only)**: 56 of 152 expected tables are absent. All seven runtime-promotion
  tables are among them, so the fault is the whole family. 49 others are absent too; one of them
  (`healing_proposals`) was dropped on purpose. The rest are not judged. Details are in the proposal.
- **Plan**: [docs/proposals/runtime_promotion_schema_repair.md](proposals/runtime_promotion_schema_repair.md). Proposed, not approved.
- **Do not**: Downgrade, edit `alembic_version` by hand, or run `alembic stamp head`. Stamp only changes the
  record. It does not create tables.
- **Next, if authorized**: Confirm the live database identity. Check whether old data must be recovered.
  Then write a forward-repair migration for both tables, with the original constraints and indexes and
  the security policies. Test it on a copy of the drifted state and on a correctly migrated state.
  Keep the service-key gate. Verify the schema and an authenticated read before closing the Forge_Command finding.

## Render Build Auth Needs One Credential For Two Private Repositories (2026-10-05)

- **Location**: `scripts/render-git-auth.sh`. The same script exists in Rake, Forge-Agents and NeuroForge.
- **Status**: Open. No change made. Not authorized.
- **What is wrong**: The script mints one installation token for `forge-telemetry` and
  `forge_contract_core` together (`PRIVATE_REPOS`, and the `repositories` request body). The
  credential must have access to both repositories.
- **Why it matters**: On 2026-10-05 a new GitHub App, `BDS Contract Core Reader` (App ID 5194470),
  was installed with `contents: read` on selected repositories. It is for PIN-2 release-mode
  parity in Forge_Command. It is not for Render builds. If an operator puts it in
  `FORGE_PRIVATE_DEPS_APP_CLIENT_ID`, GitHub rejects the `forge-telemetry` request and the build fails.
  Do not broaden that App to make the script work.
- **Proposed fix, not started**: Split the credentials. A new pair, `FORGE_CONTRACT_CORE_APP_CLIENT_ID`
  and `FORGE_CONTRACT_CORE_APP_PRIVATE_KEY`, serves `forge_contract_core` only. The existing
  credential serves `forge-telemetry` only. Each token gets its own path-scoped Git credential entry.
  Tests must show that the contract-core token cannot read `forge-telemetry`, that a missing or invalid
  key fails the build, and that no token appears in logs. The legacy PAT stays as a migration fallback only.
- **Scope**: Open for all four repositories. A plan in `docs/plans/` must come first.
- **Do not**: Change Render environment variables before the code reads the new pair.

## The Test Suite Reaches Hosted NeuroForge When `NEUROFORGE_URL` Is Unset (2026-10-04)

- **Location**: `app/config.py:107` (the default of `NEUROFORGE_URL`), `app/utils/embeddings.py:26` and `:126`
  (the endpoint and the unauthenticated `httpx` POST), and `tests/test_integration/test_infrastructure_health.py`
  (`test_embedding_generation` and `test_embedding_batch_generation`). Line numbers are for `dac5e835ec8b9b7f15e383b8621645f44a0c4d8c`.
- **Status**: **Closed (2026-10-05).** The decision owner accepted the repair evidence on 2026-10-05: the isolated runner merged as
  `038a82f6c13ba026eef98ddae739b791cdd69d37`, its final independent review, the full-suite and CI runs under the runner, the
  planted-violation run and the teardown results (see the notes at the end of this entry). The coverage gaps and follow-ups in the
  next entry stay open. Status before 2026-10-05: open, not repaired. It was
  found as finding M1 of the security review of pull request 88 (the WP-DF-00 pin bump), and the working session verified it
  against the saved outputs and the source before it was reported.
- **What is wrong**: `NEUROFORGE_URL` defaults to the hosted service `https://neuroforge-9lxc.onrender.com`. `tests/conftest.py` sets
  defaults for the database URL, the startup flag, the secret key and an OpenAI key, and none for `NEUROFORGE_URL`. A run of the suite
  with the variable unset therefore sends real HTTP requests to the hosted service. The suite gives no warning.
- **Root cause**:
  - The client has no offline mode and no allowlist of hosts.
  - The two tests call the real client. Each wraps the call in `except Exception` and calls `pytest.skip(...)`, so a failed or
    refused call shows as a skip. The call and its failure are easy to miss.
  - In a run where other tests failed, other paths that reach the embedding call (a search path, an identity flow) also produced
    502 embed errors. The reach of the suite is therefore wider than the two named tests.
- **Confirmed**:
  - In each of eight suite runs (four sequential runs of WP-DF-00, four earlier concurrent runs that were discarded), the saved
    output shows the error text `NeuroForge embed error (HTTP 401)` twice. The skip messages are `Embedding service not available:
    502: NeuroForge embed error (HTTP 401): {"schema_version":"operational_error.v1","code":"UNAUTHENTICATED","safe_message":"API
    key required",...}`.
  - One further discarded run (a PostgreSQL run whose migration collided with another run in one cluster) shows the error text 26
    times: 16 with HTTP 401, 7 with HTTP 403 and 3 source lines in tracebacks. In that run at least one test
    (`test_identity_flow_reaches_authenticated_profile`) failed with a 502 embed error instead of skipping. Its `httpx` log lines
    show `POST https://neuroforge-9lxc.onrender.com/api/v1/embed` with 403 and 401 answers.
  - No request line to any other host appears in any saved output. Documentation links to other hosts appear in the test output,
    and nothing requested them.
- **Payload and credentials**: the payloads were synthetic test strings (`"test text"` and `["text1", "text2", "text3"]`). The embed call
  adds no header, so the requests were **unauthenticated**. No credential was sent. The two credential-like variables in the
  working environment were a password-store path and a harness token, and this code does not read them.
- **Not measured**: the **number of requests**. It is at least two for each suite run. The discarded run in which tests failed
  shows more. The count was not captured.
- **Affected evidence**: the WP-DF-00 evidence runs for pull request 88 (the baseline and candidate suites, SQLite and PostgreSQL,
  and the discarded runs). The result of that evidence is not affected, because the two tests do not use `forge_contract_core` and skip
  the same way in the baseline and the candidate. The authorization for those runs prohibited live service calls, so the runs did
  not follow it. The decision owner's ruling of 2026-10-04 on D-I3 does not retrospectively authorize the calls.
- **Corrections made to the pull request description (pull request 88, after the merge)**: the description first said that the two
  tests were "not run" and that "the live-service tests are prohibited here". That was wrong. They ran, reached the hosted service
  and skipped on its error. The description first said that every call got HTTP 401. That was true for eight runs and not for
  the discarded run, which also had HTTP 403 and failing tests. The description first said that the only hostname in the saved
  outputs was the hosted one. The corrected statement is that no request to any other host appears. The description now carries a
  correction at its top. The records are in `forge_contract_core` `doc/rfcs/RFC-FC-PRC-01-r3-review-register.md`, section 20.3 (merged), and section 21 (the decision owner's rulings of 2026-10-04), which was in the open `forge_contract_core` pull request 172 when this entry was written.
- **Not checked**: whether any other test can reach a hosted service. `app/config.py` has other defaults that name hosted services
  (for example `SUPABASE_API_BASE` at line 124). They were not examined, and no request to them appears in the saved outputs.
  The saved outputs are on the working machine and are not stored in this repository.
- **Inference, not a finding**: the production service is meant to call NeuroForge (the comment in `app/config.py` says that all AI
  operations route through it). The defect is that the **test suite** does this without an explicit opt-in. This entry does not
  claim a production defect.
- **Condition for any later run**: the decision owner ruled on 2026-10-04 that a future test authorization requires network isolation
  that prevents access to hosted services and permits only explicitly identified local test services. Overriding `NEUROFORGE_URL`
  or deselecting the two tests alone does not prove that the whole suite is isolated.
- **Scope**: the DataForge test suite, for any run with `NEUROFORGE_URL` unset. Closed on 2026-10-05: the suite in `tests/` runs only under the
  isolated runner (direct `pytest` exits 87), and the decision owner accepted the evidence. `app/tests/` has no gate on master (see the
  next entry).
- **Status note (2026-10-04, implementation in review; superseded)**: the design of `docs/proposals/M1_TEST_ISOLATION_REPAIR_DESIGN.md`
  was implemented on branch `feat/m1-isolated-test-runner` (`scripts/run-tests-isolated.sh`).
  **Update (2026-10-05, merged)**: pull request 91 merged as `038a82f6c13ba026eef98ddae739b791cdd69d37` (tree equal to PR head
  `34a6b1299a5818316bb708b5fc6a5ee96a2fa9f9`). **Update (2026-10-05, closed)**: the decision owner accepted the repair evidence. M1 is closed.
  The two status notes below are history. The threat model and the final review stay current.
  (History.) M1 stayed open until the separately authorized closure evidence existed. The closure evidence is a full run of the suite
  under the runner with zero violations, and an independent review of the exact head. (The update below records the first full runs.)
  **Update (2026-10-05)**: a local full run under the runner (`--database postgres --migrate`) and the first CI full run showed
  1050 passed, 23 skipped and no violation. The 14 skips with no declared reason are now declared by their exact reason strings,
  with one entry per reason in `DECLARED_SKIPS` (`scripts/isolated_test_runner.py`). Eight of them are infrastructure-health tests
  that skip because the `db` fixture is a fixed SQLite engine. (Corrected 2026-10-05: seven skip because of the fixture, and one
  because of the psycopg 3 and psycopg2 mismatch. See the next entry.) That coverage gap exists without the runner. The direct callers
  of pytest now use the runner, and the Render build skips the suite (`scripts/preflight.sh --no-tests`). (History.) M1 stayed open until
  the closure steps were reviewed.
  **Threat model**: the guard and the plugin are in-process Python. They are defence in depth against accidental calls, not
  against a hostile test process. The kernel layers are the barrier: the network namespace, the mount allow-list, the seccomp
  filter and the absence of inherited sockets. A hostile test can truncate `violations.jsonl` or silence the stderr marker.
  That can erase only the record of an attempt that the kernel already blocked. A hardening option is a write-only pipe that
  the runner drains. Residue: `DOCKER_HOST` is limited to `unix://`, and a `docker.sock` that forwards to a remote TCP host is not detected.

- **Final review of the merged runner (2026-10-05)**: an independent review of `038a82f6` found no safety or fail-open defect
  (verdict: approve with changes; none blocks). Evidence: canaries 54 passed on each route, host canaries 39 passed, the full
  suite under the runner 1050 passed and 23 skipped with every skip declared and no violation, the planted-violation tool exit 87
  with two violations and two failed tests, and clean teardown after every normal run. CI: the runner step passed on PR run
  37265341309 and master run 37266293444. **The coverage upload failed in both** (`codecov/codecov-action@v3`, TLS handshake
  failure). The step is advisory, so no Codecov upload has succeeded for this code. The follow-ups are in the next entry.

## Follow-ups of the M1 Runner Review (2026-10-05)

- **Location**: `scripts/isolated_test_runner.py`, `scripts/prove_planted_violation.py`, `scripts/preflight.sh`,
  `tests/isolation/services.py`, `tests/isolation/canary/host/check_runner_host.py`, `.github/workflows/test.yml`,
  `tests/conftest.py`, `doc/system/15-testing.md`. Line numbers are for `038a82f6`.
- **Status**: **Open. Not repaired.** Found by the independent review of the merged runner. None is a path to a hosted service.
- **PostgreSQL coverage (open, not repaired by declaring skips)**: eight infrastructure-health checks never run on any backend.
  Seven skip because the shared `db` fixture is a fixed in-memory SQLite engine. `test_psycopg_available` skips for another
  reason: it imports psycopg 3, and the repository pins `psycopg2-binary` only. Declaring their skips does not give PostgreSQL coverage.
- **Recorded deviation**: the disposable Postgres container uses trust authentication over its Unix socket (no password), not the
  design's random credentials. The protection is `--network none`, the 0700 run directory and the identity check.
- **Misleading CI comment**: on pull requests, `test.yml` posts "Tests passed! Coverage reports available." whenever `coverage.xml` exists, although
  every upload so far has failed.
- **Signal leftovers**: after SIGTERM or SIGINT, `prove_planted_violation.py` leaves a `/tmp/dfi-*` run directory, and it never
  deletes its `planted-proof-*` temporary directory. `rmtree` on the run directory has no check that the path starts with `/tmp/dfi-`.
- **Host-canary cleanup can hit another run**: the module fixture deletes every `/tmp/dfi-*` that appeared during the module, so a
  concurrent run from another session can lose its live run directory (it then fails closed).
- **Unproven capabilities**: `tests/isolation/services.py:95-96` grants five capabilities, and the comment at line 94 says that the
  image entrypoint needs all five. The review ran the canaries with only `CHOWN`, `SETUID` and `SETGID`, and they passed. So
  `DAC_OVERRIDE` and `FOWNER` are unproven.
- **`--no-tests` is not tied to Render**: any caller can run `preflight.sh --no-tests` and see "PRE-FLIGHT PASSED". `run_isolated`
  also overwrites a caller's `ISOLATED_RUNNER_PYTHON`.
- **Stale text**: `doc/system/15-testing.md` still says "The runner has no proof for a full run of the suite."
- **Earlier gaps, noted only**: `alembic heads` failing passes the single-head check; the Makefile has literal `\t`; exit 1 also keeps
  the run directory, and the docs list only 86, 87 and 88; `app/tests/` has no gate (decision pending).
- **Scope**: open until bounded, authorized changes fix them. Each needs its own evidence.

## The CI App Credential Can Mint Organization-Admin Tokens (2026-10-05)

- **Location**: `.github/workflows/test.yml` (the step "Mint an app token for the private forge-* dependency clones") and the
  repository secret `FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY`.
- **Status**: **Open. Not repaired.** Found by a read-only inventory on 2026-10-05.
- **What is wrong**: the step mints a token of the GitHub App `bds-fleet-operator` (app id 4425224, installation 149850721). The
  installation covers all repositories of the organization and grants, among others, administration, secrets, workflows and contents
  write, and organization administration and organization secrets write. The step asks for two repositories, but the private key
  in this repository's secrets can mint a token with the full installation scope. Any workflow in this repository that can read the
  secret can therefore act with organization-admin rights. The step also passes no `permission-*` input, so the token that it mints
  carries the full installation permissions on the two named repositories.
- **Fix (not authorized)**: a dedicated GitHub App with only the permissions that the clone needs (Contents: Read on the dependency
  repositories), or mint-time narrowing plus a protected environment. Removing this key needs the decision owner.
- **Scope**: this repository's CI and any other repository that holds the same key.

## The llm-intel Promotion Apply Route Takes No Credential (2026-10-03)

- **Location**: `app/api/llm_intel_promotion_application_router.py`, routes
  `POST /api/v1/llm-intel/promotion-application/decisions/apply`,
  `GET .../promoted-records` and `GET .../promoted-records/{promoted_record_id}`.
  The router is mounted without a dependency at `app/main.py` (`include_router`).
- **Status**: Open. Confirmed in source and in an in-process run. Not fixed. This entry
  authorizes no code change. Found while tracing how DataForge validates a Forge Command decision
  receipt for plan `BDS-FC-PRC-OPT-v0.2`.
- **Confirmed**:
  - The apply route has one dependency, `get_db`. It has no authentication dependency.
    The app adds no authentication middleware (`main.py` adds timeout, correlation ID,
    compression, CORS and security headers only).
  - An in-process run of DataForge at `a0fd1665dedecfedad82dcaf646dd8a5d2a58659`, with an in-memory
    database, answered the apply route with no credential. An empty payload gave HTTP 422 from
    payload validation. No authentication step ran first. The read route gave HTTP 200 with no
    credential. The sibling `bds/sessions` route gave HTTP 401 in the same run, so the test
    harness does enforce authentication where the code asks for it.
  - On the deployed host (`dataforge-pzmo.onrender.com`), `GET .../promoted-records?limit=1` with no
    credential gave HTTP 200 and a 2-byte body. The `bds/sessions` control gave HTTP 401.
  - No gateway authenticates the path. `render.yaml` runs the app directly. `nginx.conf` is the
    docker-compose proxy and has no authentication step.
- **Inferred, not directly exercised**: the deployed `decisions/apply` route is also open. The
  deployed app uses the same route code, and no upstream layer authenticates. No `POST` was sent to
  the deployed host. A `POST` would risk a write, and the evidence above is enough for this entry.
  Do not send a production `POST` to turn the inference into direct proof.
- **Impact**: High unless a network control that this entry did not see blocks the path. Any caller
  that can reach the host could submit a promotion decision. The service stores `operator_id` and
  `authority_ring` as the caller wrote them and verifies no signature. An `approve` decision
  promotes a candidate and can project a pricing value onto `model_catalog`
  (`_project_promoted_pricing_to_catalog`). The deployed read route returned an empty body of
  2 bytes. Whether the host holds real data was not checked.
- **Cause**: The router never had an authentication dependency. Other routers (BDS sessions, cloud
  image state, and since 2026-10-01 the runtime-promotion candidate routes) use a scoped service
  key. See the entry on runtime-promotion candidate routes (FC-RT-20260930-012).
- **Fix**: Not done. The same shape as FC-RT-20260930-012 would apply: a service key bound to
  `forgecommand`, a read scope for the two `GET` routes and a decide scope for `apply`, with no key
  giving 401 and a wrong service or scope giving 403. The caller, the operator identity and the
  maximum authority ring should come from the credential and not from the payload. Decide before
  go-live.
- **Related**: `RFC-FC-PRC-01` in forge_contract_core (Proposed, not approved) makes these rules
  normative for a new apply path. The existing route is not that path and is not changed by it.

## A Non-Approve Decision Overwrites the State of a Promoted Candidate (2026-10-03)

- **Location**: `app/services/llm_intel_promotion_application.py`. The non-approve branch of
  `_apply_promotion_decision` (about lines 195 to 213), the terminal-state check (about line 215),
  and `_mark_candidate_and_drift_reports` (about line 447).
- **Status**: Open. **Confirmed by a scratch-database test on 2026-10-03.** Not fixed. No code
  change is authorized by this entry. A fix proposal is separate.
- **What the source shows**: `TERMINAL_CANDIDATE_STATES` includes `promoted`. The check against it
  runs only after the non-approve branch has returned. A decision other than `approve` with a new
  `decision_id` reaches `_mark_candidate_and_drift_reports`. That function assigns
  `promotion_state` on the candidate and on every drift report with no check of the current state.
- **Test evidence**: A read-only test ran against DataForge `a0fd1665dedecfedad82dcaf646dd8a5d2a58659`
  with an in-memory SQLite database, no network and no credential. The database was rebuilt for each
  case. Each case first promoted the candidate, then took a snapshot of four tables (candidates,
  drift reports, promoted records and decisions), applied one more decision, and took a second
  snapshot.
  - Control, `approve` again with a new `decision_id`: refused with
    `PromotionApplicationConflictError` ("already in terminal state 'promoted'"). No row changed.
  - Control, `approve` replayed with the same `decision_id`: returned `duplicate`. No row changed.
  - `reject` with a new `decision_id`: returned `recorded_no_promotion`. The candidate
    `promotion_state` changed from `promoted` to `rejected`. The drift report `promotion_state`
    and its `payload` changed the same way. One decision row was added.
  - `defer` with a new `decision_id`: the same result, with the state `deferred`.
  - Also seen, outside the two requested cases: `request_more_evidence` gave
    `more_evidence_required`, and `rollback_request` gave `rollback_requested`, on the same
    candidate and drift report fields.
  - In all four cases the promoted-record row did not change. The test did not snapshot the
    supersession chain table or `model_catalog`.
- **Impact**: A promoted candidate can be shown as `rejected`, `deferred`, `more_evidence_required`
  or `rollback_requested` while its promoted record stays in place. The state of the candidate and
  its drift report then disagree with the promoted record. The route takes no credential (see the
  entry above), so any caller could trigger it.
- **Open question**: whether `rollback_request` on a promoted candidate is meant to move the
  candidate to `rollback_requested`. The code allows it, and no test or schema in the code read says
  that it is a defect. The owner decides. `reject`, `defer` and `request_more_evidence` on a
  promoted candidate have no such reading.
- **Fix**: None. The smallest guard is a proposal, not a change: refuse `reject`, `defer` and
  `request_more_evidence` for a candidate in a terminal state, as the approve branch already does.
  Leave the `rollback_request` meaning to the owner.
- **Related**: `RFC-FC-PRC-01` in forge_contract_core (Proposed) requires that a new apply path never
  alter the stored state of a candidate that has an applied terminal decision.

## A Documentation-Only Push Still Redeploys on Render, and Security Scans Are Advisory (2026-10-02)

- **Location**: `render.yaml` (both services, `branch: master`, no `autoDeploy` or `buildFilter` key);
  `.github/workflows/security.yml`
- **Status**: Render part mitigated in `render.yaml` (2026-10-02), not yet observed. Open until a
  real documentation-only push is seen to skip the build. The Render dashboard setting is unchecked.
  The security-scan part is still open. Found while applying the 2026-10-01 rule that a
  documentation-only change runs no code CI.
- **Impact**: GitHub Actions no longer runs the code CI for a documentation-only change. Render
  still builds and deploys on every push to `master`, because `render.yaml` sets no `buildFilter`.
  The Bandit, Safety, OWASP and TruffleHog jobs all set `continue-on-error: true`. A finding never
  fails a run, so a leaked secret does not block a merge.
- **Cause**: Render deploy settings live in `render.yaml` and the Render dashboard, not in a
  workflow. The scan jobs were set to advisory in earlier changes.
- **Fix**: Done for Render, before go-live. Each service in `render.yaml` has a `buildFilter` with
  `ignoredPaths`. The paths cover root `*.md`, `doc/**` and the `docs/` directories that no test
  reads. Render ignores a path over any include rule, so `docs/plans/DFG_GOV_01/**` and
  `docs/archive/TELEMETRY_INTEGRATION_STATUS.md` stay out of the list and still build. A service
  that someone made by hand in the Render dashboard ignores `render.yaml`. Check that the Blueprint
  manages both services. Decide separately whether the TruffleHog job must fail the run.
- **Also noted**: `security.yml` keeps its existing weekly `schedule`. `deploy.yml` uses old action
  versions (`docker/*@v2`, `v4`). `test.yml` uses `codecov/codecov-action@v3`.

## Runtime-Promotion Candidate Routes Took No Credential (FC-RT-20260930-012)

- **Location**: `app/api/runtime_promotion_candidate_router.py` (all four routes: list, detail, `approve`, `reject`)
- **Status**: Fixed in code 2026-10-01, pending merge. **Not live until Forge Command sends a key.**
- **Impact**: High before the fix. Any caller could read candidate evidence and write an
  approve or reject decision. An approve could also create an execution handoff request.
  Found by Forge Command (finding FC-RT-20260930-012): the deployed list route answered 500, not
  401, with no credential.
- **Cause**: The router had no authentication dependency. Other routers (BDS sessions, cloud image
  state) already use a scoped service key.
- **Fix**: Every route now needs a service key bound to `forgecommand`. Read needs
  `runtime-promotion:candidates:read`. Approve and reject need
  `runtime-promotion:candidates:decide`. No key gives 401. A wrong service or scope gives 403.
  The recorded operator identity comes from the key, not from the request body.
- **Tests**: 6 new tests (no key, unknown key, read-only key, other service, refused decision
  changes nothing, spoofed identity). The 26 candidate and worker tests pass. Five identity and
  login tests fail with and without this change.
- **Rollout order**: Forge Command must send the key first. Then mint the key in Forge Command
  Settings with both scopes and service `forgecommand`. Then merge this change. If this merges
  first, Forge Command recommendations fail closed with an upstream 401.
- **Still open**: The receipt-ingest route `POST /api/v1/runtime-promotion/receipts/local-failure-pattern`
  still takes no credential. The tests call it with no key and it answers 201. It creates
  candidates. The other routes in `runtime_promotion_router.py` were not read in this change.

## Hosted CI Fails Before Any Job Step Runs

- **Location**: `.github/workflows/test.yml`, `docker.yml`, `security.yml` (every hosted job)
- **Status**: Open. Recorded 2026-09-29. **A deep audit is deferred by operator decision**
  (2026-09-29): work continues on local verification until the audit.
- **Impact**: High. No hosted check verifies any change. Observed on `master` at `5b2219f` and on
  PR heads `18f5d3e` (#77) and `a56f375` (#78): every job concludes `failure` about 2–5 seconds
  after it starts. Check-run output is empty, job-log downloads return HTTP 404, and one re-run on
  each PR failed the same way. #77 and #78 merged on local evidence only.
- **Cause**: Unknown. The check runs report annotations that were not readable through the API.
  An account, billing, or runner setting is a hypothesis, not a finding.

### Audit scope (deferred)

1. Read the job annotations and the Actions settings (billing, spending limit, runner
   availability, workflow permissions) in the GitHub UI.
2. Restore hosted runs, then re-run CI on `master` and confirm each workflow passes.
3. Re-verify every change merged on local evidence while CI was down, starting with #77 and #78,
   against hosted results.
4. Reconcile the 9 local test failures that also fail on `master` (auth and profile tests on the
   SQLite harness, `no such table: users`).

## ForgeEvent.v1 Ingest Does Not Enforce the RFC-FT-04 AI Profile

- **Location**: `app/api/telemetry_router.py` (`ingest_forge_event_v1`),
  `app/models/telemetry_schemas.py` (`ForgeEventV1Submission`)
- **Status**: Enforcement implemented on the corrective candidate branch
  (2026-09-29, later); closes when that change merges. Recorded 2026-09-29 by the
  RFC-FT-04 candidate proof (`scripts/prove_rfc_ft_04_candidate_postgres.sh`).
- **Impact**: Low while the profile is a candidate. The ingest boundary validates
  the `ForgeEvent.v1` envelope only. It stores an event that declares
  `ForgeAIInferenceSemantics.v1` and breaks the profile (the proof stores one
  with an unknown `ai.execution_lane` key). Storage success is therefore not
  profile validation. Producers must validate the profile before emission.
- **Cause**: The profile is not admitted, and RFC-FT-04 §5 lists no DataForge
  change.

### Suggested Fix

Decide at admission whether DataForge enforces the profile at ingest. If it
does, that is a separate, authorized DataForge change. Until then, a consumer
must not treat a stored profile event as profile-valid.

### Fix (corrective pass, 2026-09-29)

The operator ruled that DataForge enforces the profile at ingest.
`app/services/forge_event_profiles.py` rejects undeclared `ai.` keys,
unadmitted profiles, and profile violations before persistence, and fails
closed when the pinned validator is unavailable. No profile is admitted, so
ordinary runtime rejects every candidate event. The validator is
forge_contract_core's module, vendored byte-for-byte and SHA-256 pinned.

**Still open:** the vendored validator is loaded with `exec` of the hashed
bytes (bandit B102, suppressed with `nosec`). Once a pinned forge-contract-core
release carries the validator, replace the vendored copy with a normal import.
Events stored before this change are not re-validated.

## A Partial Local Virtualenv Is Committed Under `.venv/`

- **Location**: `.venv/` (37 tracked files: `pyvenv.cfg`, `bin/*`, `lib64`, one
  `include/` header), `.gitignore:9`, `scripts/preflight.sh:33-40`
- **Status**: Open. Found on 2026-09-28 while running the preflight for
  DataForge#75. Present on `master` at `a4e8b33`.
- **Impact**: Low to medium, and it depends on the host. `.gitignore` already
  lists `.venv/`, but PR #28 (merged 2026-07-15, `145ccf3`) committed 37 files
  under it. The tracked files are the operator's local environment:
  - `pyvenv.cfg` names Python 3.12.3 and the path
    `/home/charlie/Forge/ecosystem/DataForge/.venv`.
  - Every console script (`pytest`, `alembic`, `uvicorn`, and more) starts with
    `#!/home/charlie/Forge/ecosystem/DataForge/.venv/bin/python`. On any other
    host, running one fails with "bad interpreter".
  - `bin/python` links to `/usr/bin/python3`, so on most hosts it is
    executable. `scripts/preflight.sh` then finds `.venv/bin/python` and
    activates this partial virtualenv. `lib/` is not tracked, so it has no
    installed packages until the preflight's `pip install` step fills it.
  - Running `python3 -m venv .venv` in a fresh clone rewrites tracked files,
    so the working tree shows them as modified.
- **Cause**: The files were added in spite of the `.gitignore` rule, probably
  with `git add -f` or a broad `git add` on a branch where the rule was absent.

### Suggested Fix

Remove the files from the index and keep the ignore rule:
`git rm -r --cached .venv && git commit`. The operator's local `.venv` stays
on disk. No code, test, or workflow reads a tracked `.venv` path.

---

## `SessionData` Mixes Naive and Aware Datetimes, So `get_session` Returns None

- **Location**: `app/utils/session_manager.py` (`SessionData.created_at`,
  `SessionData.last_activity`, `SessionData.is_expired`),
  `app/tests/test_api_deployment.py`
- **Status**: Open. Found on 2026-09-24 while fixing the load balancer port
  default (see the next entry). It also fails on `master` at `6dc0736`.
- **Impact**: Low today. The session manager serves only
  `api_deployment_router`, which `app/main.py` does not mount. Five tests fail:
  `test_get_session`, `test_session_expires`, `test_update_session_data`,
  `test_set_affinity`, and `test_session_count`. No gate runs them, because
  `pytest.ini` collects only `tests/`, not `app/tests/`.
- **Cause**: `created_at` and `last_activity` default to `datetime.utcnow()`,
  which is naive. `is_expired` and `touch()` use `datetime.now(UTC)`, which is
  aware. The subtraction raises `TypeError` ("can't subtract offset-naive and
  offset-aware datetimes"). `get_session` catches the error, logs it, and
  returns `None`.

### Suggested Fix

Make both defaults aware: `field(default_factory=lambda: datetime.now(UTC))`.
`InstanceMetrics.timestamp` in `app/utils/load_balancer.py` uses the same naive
default. Then decide if `app/tests/` must join a gate, so that a break like this
one fails a check.

**Status note (2026-10-05)**: the direct-pytest part is closed. The repository-root `conftest.py` now calls the
isolation gate (`tests/isolation/gate.py`), so `pytest app/tests` without `scripts/run-tests-isolated.sh` exits 87
before any `app` import. `app/tests/conftest.py` calls the same gate, which closes `--confcutdir app/tests`.
The gate stops an accidental direct run only. It is not a barrier against a deliberate bypass: `--noconftest`, a
`--confcutdir` below the root conftest elsewhere, `-p` with a plugin that imports `app`, those options through
`PYTEST_ADDOPTS`, `python -m unittest` and plain `python <file>` all skip it (doc/system/15-testing.md, Known limits).
Collection of `app/tests/` by `testpaths` or CI stays an open decision. The five failures above are still open.

---

## The Load Balancer Defaulted an Instance to Port 8000, the NeuroForge Port (Resolved 2026-09-24)

- **Location**: `app/utils/load_balancer.py` (`APIInstance.port`),
  `app/api/api_deployment_router.py` (`APIInstanceRegisterRequest.port`)
- **Status**: RESOLVED on 2026-09-24. The forge port check
  (`scripts/check-port-registry.py`, forge `KI-FORGE-20260924-003`) found the
  `APIInstance` default.
- **Impact**: Low. An instance registered without a port pointed at 8000,
  which the forge `PORT_REGISTRY.md` gives to NeuroForge. A DataForge API
  instance listens on 8001. `app/main.py` does not mount
  `api_deployment_router`, so no live route used the default.
- **Cause**: The default is older than the port registry.

### Fix

Both defaults are 8001. `app/tests/test_api_deployment.py` asserts the
`APIInstance` default.

---

## DataForge's Own Default Port Was 8788, Not the Registered 8001 (Resolved 2026-09-24)

- **Location**: `app/config.py` (`PORT`), `app/main.py` (`__main__` block),
  `docs/guides/`, `docs/setup/`
- **Status**: RESOLVED on 2026-09-24. The forge port check
  (`scripts/check-port-registry.py`, forge `KI-FORGE-20260924-003`) found it.
- **Impact**: Low, local only. `python -m app.main` without `PORT` bound 8788,
  the port DataForge used before the forge `PORT_REGISTRY.md` existed. The
  registry, this repository's `doc/system` (`14-config-env.md`),
  `.env.example`, both compose files, and the clients in ForgeAgents and
  AuthorForge use 8001. A client with the registry default could not reach
  DataForge started that way. Render sets `PORT` itself, and the compose
  files and `.env.example` set 8001, so those runs were not affected.
- **Cause**: The two code defaults are older than the port registry
  (2026-02-24), and nothing compared them with it. The operational guides
  in `docs/guides/` and `docs/setup/` repeated 8788.

### Fix

- `app/config.py` and `app/main.py` default `PORT` to 8001.
- The operational guides in `docs/guides/` and `docs/setup/` use 8001 (69
  mentions in 10 files). The historical snapshots in `docs/references/`,
  `docs/archive/`, and `.claude/` stay unchanged as a record.
- In the same change set, NeuroForge and rake give the local DataForge URL
  as 8001 instead of 8788.

**Verified:** `bash scripts/preflight.sh` passes: a single Alembic head, the
poller and AuthorForge boundary tests (72 passed), and the unit tests
(575 passed, 5 skipped).

---

## No Expiry Alerting for Issued API Keys

- **Location**: `app/auth/api_keys.py` (`api_keys` table, `create_api_key`, `validate_api_key`)
- **Status**: Confirmed 2026-08-27 (Cost Provenance Tranche 3 go-live). One
  specific expired key (issued 2026-06-05, expired 2026-07-05) was found and
  replaced; the class of failure is unaddressed.
- **Impact**: High, silent. Every consumer of a DataForge-issued API key
  (NeuroForge's `/api/v1/model-outcomes` and `/api/v1/rate-cards` writes are
  the confirmed case) authenticates with a key that has a hard `expires_at`
  and no rotation reminder. The key found expired had sat unrotated for
  seven weeks before anyone noticed — not because anything alerted, but
  because an unrelated production investigation happened to probe it. Every
  authenticated write from the consuming service failed with a 401 for that
  entire window; the caller's own error handling (by design, cost
  accounting must never break on a failed write) logged and swallowed it,
  so nothing surfaced upstream either.
- **Cause**: `api_keys` tracks `expires_at`/`last_used_at`/`revoked_at` per
  row, but nothing reads that data proactively — only `validate_api_key`
  checks it, and only at request time, after the key has already failed.

### Suggested Fix

A scheduled job (or a lightweight endpoint a health-check can poll) that
flags any active key expiring within N days, and separately flags any key
that's been *presented and rejected* recently (a strong signal a consumer
is still configured with a dead key, exactly this incident's shape). Also
worth minting `service`-tagged keys by convention going forward — the key
that expired had empty `metadata: {}`, so its original owner/purpose
couldn't be determined from the table alone and had to be inferred from
which consumer's Render env var held it.

---

## No Drift Detection Between the `bds-fleet-operator` App Key and Render's Copy

- **Location**: `scripts/render-git-auth.sh` (App-based token minting path),
  Render service environment (`FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY`)
- **Status**: Confirmed 2026-08-27. This specific instance was fixed
  (Render's copy of the key pair repasted from the current regenerated
  key); the underlying gap is unaddressed.
- **Impact**: High — every deploy fails closed with a clear error
  (`render-git-auth: ERROR - BDS Fleet Operator credentials were rejected
  by GitHub`), which is at least loud, but there's no proactive check: the
  GitHub App's private key was regenerated on the GitHub side (for a CI
  credential fix in a different repo) without anyone checking whether any
  Render service's copy of the same pair needed updating too. It does —
  the key is shared across every consumer of this App, and Render holds
  its own separate copy per service.
- **Cause**: The App private key is duplicated in at least two places per
  consuming service (GitHub Actions secrets for CI, Render environment
  variables for build-time dependency cloning), with no single source of
  truth and no automated propagation between them.

### Suggested Fix

When rotating `bds-fleet-operator`'s private key, treat "update every
Render service's `FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY`" as a required step
of the rotation, not an optional follow-up — ideally checked off against
an explicit list of every service that consumes it (currently at least
DataForge and NeuroForge for the git-auth path, plus whichever repos'
GitHub Actions secrets separately hold the CI copy).

---

## No Verification That the Assumed `onrender.com` Hostname Matches What Render Actually Bound

- **Location**: `render.yaml` (`name: dataforge`); any doc, script, or support
  ticket referencing `https://dataforge.onrender.com`
- **Status**: Confirmed 2026-08-28. `render.yaml` requests `name: dataforge`,
  but `onrender.com` subdomains are unique across Render's entire platform —
  the plain `dataforge` slug was already taken, so Render silently bound the
  real service to `dataforge-pzmo.onrender.com` at creation time instead.
  Every real client (`Author-Forge`, `cortex_bds`) has always used the
  correct `-pzmo` hostname and was never affected. But a separate production
  incident investigation and a Render support escalation both tested the
  unbound `dataforge.onrender.com` (Cloudflare has no origin route for it,
  so every path hangs indefinitely) and misdiagnosed it as a Render platform
  bug before the hostname mismatch was found.
- **Impact**: Medium. No production consumer was ever broken, but the wrong
  assumption cost a full incident investigation and a support ticket before
  the real (non-)cause was found. The same failure mode can recur for any
  service whose `render.yaml` `name` collides with an existing slug
  elsewhere on the platform.
- **Cause**: Nothing checks that a service's assumed `<name>.onrender.com`
  hostname is the one Render actually bound — `render.yaml`'s `name` field
  is a request, not a guarantee, and there's no drift check between the two.

### Suggested Fix

Record each service's actual bound hostname (from the Render dashboard's
"your service is live at" field) somewhere durable — e.g., a comment next
to `name:` in `render.yaml` — so it doesn't have to be rediscovered live
from the dashboard during a future incident. Worth checking for every other
Forge service on Render too, not just DataForge, since the same silent
suffixing can happen to any of them.

---

## No Required Branch-Protection or Status Checks on `master`

- **Location**: GitHub repository settings (rulesets), not application code.
- **Status**: RESOLVED 2026-09-13. Confirmed the same day, found while
  scoping `BDS-DF-RF-001` and independently while closing
  `BDS-RMCP-FC-GIR-v0.1`'s `A3-GATE-00B` item 2. Verified via
  `gh api repos/Boswell-Digital-Solutions/DataForge/rulesets`: only the
  org-wide ruleset `21073023` ("Protect default branches") applied —
  deletion and non-fast-forward protection only, no required pull
  request, no required review, no required status check. Fixed the same
  day: ruleset `23156479` ("Require PR and CI checks on master") now
  requires a pull request (0 approvals, matching Forge_Command's
  single-operator posture) plus eight required status checks (`build`,
  `lint`, `test`, `Bandit Security Scan`, `Dependency Vulnerability
  Check`, `OWASP Dependency Check`, `CodeQL Analysis (python)`, `Secret
  Detection`) — verified active via `gh api repos/.../DataForge/rulesets`.
- **Impact**: High. A broken commit can merge directly to `master` with no
  CI gate stopping it; Render's auto-deploy then picks it up on the next
  build. `Forge_Command` by contrast has its own additional ruleset
  (`22391709`) requiring a PR plus eight named status checks — DataForge
  has no equivalent.
- **Cause**: Nothing beyond the shared org-wide ruleset was ever configured
  for this repository specifically.

### Suggested Fix

Add a repository-scoped ruleset requiring a pull request and DataForge's
own CI job(s) (test suite, security scan, Docker build) as required status
checks, mirroring the shape of Forge_Command's `22391709`.

---

## `llm-intel/pending-records` Pipeline Is LLM-Intel-Specific, Not Yet a Generic Intake

- **Status**: RESOLVED 2026-09-14. `BDS-DF-RF-001`'s ingest service
  (`app/api/df_rf_router.py`, `app/services/df_rf_ingest.py`,
  `app/models/df_rf_models.py`) generalizes the llm-intel pipeline's
  *pattern* -- `stable_hash()`-based idempotency (imported verbatim, no
  duplication), the duplicate-vs-conflict shape, referential-integrity
  lookups before accepting a dependent record -- against three brand-new
  tables (`df_rf_evidence_links`, `df_rf_finding_candidates`,
  `df_rf_dispositions`). No llm-intel file was touched: no shared code, no
  shared tables, so the "explicit regression plan" this entry called for
  is satisfied by construction rather than needing an active regression
  test. `bash scripts/preflight.sh` confirms all 546 pre-existing tests
  (llm-intel's included) still pass unmodified, plus 17 new `df_rf` tests.
  `llm_intel_promotion_application.py`'s promotion/registry-projection
  logic was confirmed *not* to generalize at all (a materially harder
  problem OD-02 rules out for this family: terminal candidates, no
  promoted-record materialization, no supersession chain).
- **Location (new)**: `app/api/df_rf_router.py`, `app/services/df_rf_ingest.py`,
  `app/models/df_rf_models.py`, `app/models/df_rf_schemas.py`,
  `alembic/versions/20260914_01_add_df_rf_tables.py`,
  `tests/test_df_rf_ingest.py`.
- **Original location**: `app/api/llm_intel_pending_records_router.py`,
  `app/services/llm_intel_pending_records.py`,
  `app/services/llm_intel_promotion_application.py`,
  `llm_intel_pending_records_models.py` -- unchanged by this work.

### What's still honest, not fully solved

`verification_status` on `df_rf_evidence_link` records (RFC-DF-RF-01
Finding 2 -- whether DataForge actually confirmed a claimed upstream
receipt) is now real for two `upstream_family` values: `ForgeCheckRunReceipt.v1`
(`forge_check_run_receipts_v1`) and, as of 2026-09-14, `MemoryConflict.v1`
(new `memory_conflicts` table, `BDS-FMEM-OPCOURT-001` WP-01). Every other
`upstream_family` (`TelemetryEmitReceipt.v1`, `ServiceHealthEnvelope.v1`, ...)
returns `verification_unavailable` honestly rather than a fabricated
`verified` -- per the same `inconclusive`-is-not-`violated` doctrine Living
Topology V2 uses. Extending `_VERIFIABLE_UPSTREAM_FAMILIES` in
`df_rf_ingest.py` to more families as DataForge gains queryable storage for
them is additive, non-RFC implementation work, not a defect to fix now.

Forge_Command's producer-side emission (the code that actually calls
`POST /api/v1/df-rf`) is a separate, not-yet-authorized slice -- it has no
legitimate real caller yet, since `BDS-RMCP-FC-GIR-v0.1`'s Phase 1/
`A3-WP-01B` (the actual incident-evidence-collection work) remains
unauthorized, and neither does `BDS-FMEM-OPCOURT-001`'s `forge-memory`
reconciliation engine, which is still a documented skeleton (no real
`memory_conflict` event exists to write yet either). This ingest service and
`POST /api/v1/memory/conflicts` are complete and tested on their own, but
nothing calls either in production.

### Two real bugs found and fixed while wiring `MemoryConflict.v1` in (2026-09-14)

- **RLS gap on the three `df_rf_*` tables.** `20260914_01_add_df_rf_tables.py`
  (this same day, earlier) created `df_rf_evidence_links`,
  `df_rf_finding_candidates`, `df_rf_dispositions` without enabling row-level
  security, reproducing the exact drift class `20260711_01`/`20260712_03`
  exist to close. Not caught by any test, because the local suite runs on
  SQLite, which has no RLS concept -- this class of gap is invisible to
  `bash scripts/preflight.sh` by construction. Fixed in
  `20260914_02_add_memory_conflicts_and_fix_df_rf_rls.py`, which enables RLS
  (deny-all, `anon`/`authenticated` privileges explicitly revoked) on all
  three tables and on the new `memory_conflicts` table from its own creation,
  guarded by `if bind.dialect.name == "postgresql"` so SQLite tests are
  unaffected either way.
- **`_compute_verification_status` bound the wrong Python type for a plain
  string identifier column.** The original implementation parsed
  `upstream_record_id` into a `uuid.UUID` object before every lookup, which
  is what `ForgeCheckRunReceipt.v1.receipt_id` (a Postgres `UUID(as_uuid=True)`
  column) needs -- but `MemoryConflict.v1.conflict_id` is a plain
  `String(64)` column, and binding a `uuid.UUID` object against it raised
  `AttributeError` under the SQLite test backend (would very likely have
  silently mismatched rather than errored under real Postgres, which is
  worse). Confirmed by a real test failure while adding `MemoryConflict.v1`
  support, not caught by inspection alone. Fixed by inspecting the target
  column's actual SQLAlchemy type (`isinstance(column.type, sa.String)`) and
  binding the string or the parsed `uuid.UUID` accordingly, rather than
  assuming one form works for every family. A regression test
  (`test_verification_status_is_verified_against_a_string_primary_key_column`)
  pins this for both column shapes going forward.

---

## `require_bearer` on the CSSA Cloud-Security Ledger Does Not Verify the Token

- **Location**: `app/api/cloud_security_router.py::require_bearer`, used by every
  `/api/v1/cloud-security/{decisions,authorizations,outcomes}` read and write route
  (append, single-record read, list/query).
- **Status**: Open. Noted in the function's own docstring as a known deferred step
  ("verification against the ForgeCommand token authority arrives with that
  integration") -- not previously tracked here. Surfaced 2026-09-20 while scoping
  forgesentinel's first live consumer of this ledger (a poller against the list/query
  endpoint); flagged because a real external consumer is now being designed against
  this boundary, not because anything newly broke it.
- **Impact**: Medium today, will become High once any real consumer exists.
  `require_bearer` only checks that an `Authorization: Bearer <token>` header is
  present and non-empty -- any string satisfies it. There is no verification the
  token is valid, unexpired, or scoped to this service. Writes are further
  constrained by payload hash validation (a forged write still has to produce a
  self-consistent record), but the list/query and single-record read routes have no
  such backstop -- any caller who can reach this host can read the full CSSA
  decision/authorization/outcome ledger today.
- **Cause**: `require_bearer` was written to match `bugcheck_router`'s existing
  service-token posture at the time, which itself defers real verification to a
  ForgeCommand token-authority integration that has not landed.

### Suggested Fix

Wire `require_bearer` to the same ForgeCommand token-authority check other
DataForge-issued credentials use (see the admin-token / `run_token` / `user_token`
rows in this repo's `CLAUDE.md`), or, at minimum, a static shared-secret check scoped
to this router until that lands. Do this before any production consumer (forgesentinel
included) is granted a live credential against this endpoint -- tracked as part of
that consumer's own separate "bounded activation" decision, not this slice.

---

## `FORGE_TELEMETRY_TOKEN` CI Secret Is Invalid -- Blocks All Test-Suite Runs Fleet-Wide

- **Location**: `.github/workflows/test.yml::Configure git auth for private forge-* dependencies`
  (the `FORGE_TELEMETRY_TOKEN` repository secret, used to `git clone` the private
  `forge-telemetry`/`forge_contract_core` pip dependencies during CI).
- **Status**: RESOLVED 2026-09-20 for the immediate block (a correctly-scoped fine-grained
  PAT was re-pasted into the `FORGE_TELEMETRY_TOKEN` secret, confirmed by a green `test` run),
  and the root cause fixed the same day by removing the static PAT from CI entirely --
  `test.yml`/`docker.yml`/`deploy.yml` now mint a short-lived, repo-scoped installation token
  from the org's `bds-fleet-operator` GitHub App per run (`actions/create-github-app-token@v2`),
  mirroring `Forge-Agents/.github/workflows/ci.yml` and this repo's own `render-git-auth.sh`
  (which already did this for Render builds). Needs `FORGE_PRIVATE_DEPS_APP_CLIENT_ID`
  (repo variable) and `FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY` (repo secret) added to this repo's
  Actions config before the new workflow steps can run -- not yet confirmed set as of this
  write-up. `FORGE_TELEMETRY_TOKEN` itself is left in place, unused by the new steps, until
  that's confirmed working end to end.

  Original finding, kept for provenance: found while getting an unrelated docs-only PR (`#71`)
  to a green merge -- its `test` check failed twice in a row (a fresh re-run, not a flake) with
  `remote: Invalid username or token. Password authentication is not supported for Git
  operations. / fatal: Authentication failed for
  'https://github.com/Boswell-Digital-Solutions/forge-telemetry.git/'`. The workflow's own
  guard step (which would print `::error::FORGE_TELEMETRY_TOKEN secret is not set`) did not
  fire, so the secret existed but its token value was invalid -- not simply missing. Confirmed
  unrelated to any code change: `master`'s own `Test Suite` last succeeded on this exact head
  commit (`89fc959c`) at 2026-09-19T05:52 -- something about the token broke between then and
  2026-09-20. Re-pasting the token's value initially still 403'd with "Write access to
  repository not granted" even though the token's own settings page showed correct
  repository access and `Contents: Read` -- the actual cause was a stale/mismatched value
  having been pasted, not a misconfigured token; regenerating and re-pasting that exact
  token's value fixed it.
- **Impact**: High. Every PR's `test` job fails at the dependency-install step before a single
  test runs, and `test` is one of the eight required status checks
  (`23156479`, "Require PR and CI checks on master") added 2026-09-13 specifically to stop a
  broken commit merging silently. Right now that protection itself blocks *every* PR, including
  ones with zero code risk (like `#71`, a single-markdown-file docs change) -- an admin override
  would defeat the exact protection this repo added a week ago, so this needs a real fix, not a
  bypass.
- **Cause**: `FORGE_TELEMETRY_TOKEN` is a fine-grained GitHub PAT with `Contents:Read` on
  `Boswell-Digital-Solutions/forge-telemetry` (and `forge_contract_core`). Fine-grained PATs
  expire on a fixed schedule (unlike the org's GitHub App-based credentials elsewhere) and have
  no drift/expiry alerting -- the same class of gap as this file's own "No Expiry Alerting for
  Issued API Keys" entry above, just for a CI secret instead of a DataForge-issued one.

### Suggested Fix

Done. `test.yml`/`docker.yml`/`deploy.yml` mint a `bds-fleet-operator` App installation token
per run instead of reading a static PAT secret -- the same class of fix already applied for
Render (`render-git-auth.sh`) and for Forge-Agents' own CI. Remaining step: confirm
`FORGE_PRIVATE_DEPS_APP_CLIENT_ID`/`FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY` are set on this repo
(same App credential pair Render already uses) and that a real CI run mints and uses the
token successfully; once confirmed, `FORGE_TELEMETRY_TOKEN` can be deleted as a repo secret
-- nothing will reference it any more.

---

_Last updated: 2026-09-20_

## Model findings pilot intake

Pilot: `BDS-MODEL-FINDINGS-TOP10-v0.1`. See [the review checklist and evidence rules](MODEL_FINDINGS_PILOT.md) and [session log](model-findings/sessions.yaml).

Initial phase: **`baseline_after_merge`**. During the comparison baseline, continue normal issue handling. During structured intake, record each distinct model-raised concern here or link it to an existing record before closing the review. Untested claims are **unverified**. Keep verification separate from open/deferred/closed disposition, preserve disproven claims, and require relevant evidence for fix closure. Existing entries retain their historical provenance and are not reverified by this addition.

### Pilot findings

New observations go below this heading or into existing linked entries. Setup observations are marked separately and do not count as pilot effectiveness results.
