# Cloud Image PROD-01 Reuse and Verification

**Plan:** `BDS-NF-FORGEIMAGES-PROD-001`
**Slice:** `PROD-01`
**Prepared:** 2026-09-13
**DataForge source:** `4bac10c4cce1f9a290121669866e79086108b500`
**NeuroForge source:** `3359552ab2e2cd8a1fc82a875514a8a375d0ed49`

## Authority and Reuse Matrix

| Concern | Existing surface reviewed | Decision |
|---|---|---|
| SQL transaction/session | `app.database`, SQLAlchemy services | Reuse. Domain writes use one session and one commit. |
| Migrations | Alembic single head `20260906_01` | Reuse; add one successor revision `20260913_01`. |
| Service authentication | `AuthContext`, database API keys, metadata scopes | Reuse; require exact NeuroForge service binding and dedicated read/write scopes. |
| RLS posture | Supabase table lockdown migrations | Reuse posture; enable RLS and revoke `anon`/`authenticated` access on all six new tables. |
| Run/job records | Generic run and ForgeRun tables | New domain tables. Existing records do not carry the cloud-image state graph, caller idempotency, protected request, or CAS version. |
| Events | Telemetry and CSSA ledgers | New domain event table. Existing event schemas have different authorities and cannot atomically share this job transaction. |
| Idempotency/receipts | Domain-specific receipt patterns | New domain binding and operation receipt tables so replay is atomic with the job effect. |
| Outbox | No safe generic transactional outbox found | New `cloud_image_outbox`; it is written with each event and is not a worker or dispatcher. |
| Encryption | `app.utils.data_encryption` | Do not reuse. DataForge receives no plaintext or key; NeuroForge sends authenticated AES-GCM ciphertext. |
| Rate cards | `rate_card_snapshots` | Reuse in PROD-03; no duplicate pricing authority in this slice. |
| Quota | CSSA quota reservation/consumption | Reuse or extend in PROD-03; no duplicate quota authority in this slice. |

## Delivered Contract and Transaction

The internal prefix is `/api/v1/internal/cloud-image-state`. Strict v1
contracts cover create/replay, internal or caller-scoped read, protected retry
source, expected-version transition, event append, and event read. Create and
transition and standalone event-append transactions contain the state effect,
append-only event, idempotency or operation receipt, and outbox row. Protected
request fields are limited to algorithm, key reference,
nonce/AAD/ciphertext, ciphertext digest, keyed semantic fingerprint, and
retention timestamps.

## Verification Snapshot

- DataForge focused contract, route, and multi-stage rollback tests: **22 passed**.
- PostgreSQL competing-transition test: **1 passed**; exactly one winner and one
  `compare_and_set_conflict`.
- Alembic topology: exactly one head, `20260913_01`.
- PostgreSQL upgrade from stamped `20260906_01`: **passed**, six tables present.
- PostgreSQL downgrade to `20260906_01`: **passed**, zero `cloud_image_%` tables remain.
- Clean PostgreSQL upgrade through the full history to `20260913_01`: **passed**,
  six tables present.
- NeuroForge cloud-image acceptance set after adapter wiring: **164 passed**
  (the prior 160 plus four durable-adapter tests).
- Direct cross-repository schema probe: NeuroForge create and transition
  payloads both validate against DataForge's strict v1 request models, and the
  v1 responses validate back into NeuroForge records.
- NeuroForge required gate: all functional, cloud-image, documentation,
  compile, compatibility-smoke, and resilience checks passed. Aggregate
  collection remains red because two unrelated HFX tests require the absent
  pre-existing `forge-contract-core` distribution; collection with those two
  tests excluded succeeds with 2,334 tests.

The first PostgreSQL concurrency attempt found that independent ORM objects
needed explicit parent/child flush ordering. The implementation was corrected
without adding a commit boundary; rollback remains atomic. Both the expanded
22-case contract/route/rollback suite and the PostgreSQL concurrency gate passed afterward.

## Limits and Next Gate

This implementation has not been deployed and no production key material was
created. It adds no queue consumer, outbox dispatcher, lease, provider SDK,
provider call, artifact downloader/storage, ForgeImages network call, or live
traffic. `PROD-02` remains blocked pending human acceptance of `PROD-01`.
