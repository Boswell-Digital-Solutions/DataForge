# Known Issues

This document tracks confirmed issues and concerns awaiting investigation. Blocking impact and verification status are stated per item.

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

_Last updated: 2026-09-14_

## Model findings pilot intake

Pilot: `BDS-MODEL-FINDINGS-TOP10-v0.1`. See [the review checklist and evidence rules](MODEL_FINDINGS_PILOT.md) and [session log](model-findings/sessions.yaml).

Initial phase: **`baseline_after_merge`**. During the comparison baseline, continue normal issue handling. During structured intake, record each distinct model-raised concern here or link it to an existing record before closing the review. Untested claims are **unverified**. Keep verification separate from open/deferred/closed disposition, preserve disproven claims, and require relevant evidence for fix closure. Existing entries retain their historical provenance and are not reverified by this addition.

### Pilot findings

New observations go below this heading or into existing linked entries. Setup observations are marked separately and do not count as pilot effectiveness results.
