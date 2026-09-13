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

- **Location**: `app/api/llm_intel_pending_records_router.py`,
  `app/services/llm_intel_pending_records.py`,
  `app/services/llm_intel_promotion_application.py`,
  `llm_intel_pending_records_models.py`.
- **Status**: Noted 2026-09-13 during `BDS-DF-RF-001` (Receipt-to-Finding
  Knowledge Spine v0.1) scoping. Not a defect — a design note ahead of
  planned reuse.
- **Impact**: Medium, forward-looking. The pipeline already models almost
  exactly the shape `BDS-DF-RF-001` needs (`receipt → extracted claim →
  pending candidate → drift report → promotion decision → promoted
  record`, family-tagged and idempotent at ingest via `record_family`), and
  `BDS-DF-RF-001`'s ruled implementation basis (OD-03) is to generalize
  this pipeline rather than build a separate one. But the storage/service/
  promotion logic itself is currently LLM-intel-specific, not a truly
  generic intake framework — generalizing it carries real risk of
  destabilizing the live LLM-intel flow if done carelessly.
- **Cause**: The pipeline was built for one consumer (LLM pricing-drift
  intake) and has not yet needed to serve a second one.

### Suggested Fix

When `BDS-DF-RF-001`'s `WP-01` drafts the generalized contract, require an
explicit regression plan for `llm-intel/pending-records`'s existing tests
before any shared code (models, service, promotion-application logic) is
touched. Prefer extending the `record_family` discriminator over
refactoring the underlying tables/services where possible.

---

_Last updated: 2026-09-13_

## Model findings pilot intake

Pilot: `BDS-MODEL-FINDINGS-TOP10-v0.1`. See [the review checklist and evidence rules](MODEL_FINDINGS_PILOT.md) and [session log](model-findings/sessions.yaml).

Initial phase: **`baseline_after_merge`**. During the comparison baseline, continue normal issue handling. During structured intake, record each distinct model-raised concern here or link it to an existing record before closing the review. Untested claims are **unverified**. Keep verification separate from open/deferred/closed disposition, preserve disproven claims, and require relevant evidence for fix closure. Existing entries retain their historical provenance and are not reverified by this addition.

### Pilot findings

New observations go below this heading or into existing linked entries. Setup observations are marked separately and do not count as pilot effectiveness results.
