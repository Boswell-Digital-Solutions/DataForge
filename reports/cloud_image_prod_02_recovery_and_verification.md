# Cloud Image PROD-02 Recovery and Verification

**Plan:** `BDS-NF-FORGEIMAGES-PROD-001`
**Slice:** `PROD-02`
**Prepared:** 2026-09-13
**DataForge source:** `61d5b3b411450bb911bc16d3e07fbddcaeec15d4`
**NeuroForge source:** `b4249956e27038b5df381812e1192d1d937cd96e`
**Forge source:** `a426a9d91242dbd41db449b4ceec59db392439ab`
**ForgeImages source:** `fddcc113e189061938b3433495cb006a1f301890`

## Authority Boundary

DataForge owns the durable lease, fencing token, attempt, state-transition,
event, operation-receipt, and outbox-delivery records. NeuroForge owns the job
state graph, stage meaning, retry classification, handler execution, and
provider-neutral status. ForgeImages remains the only authority that may accept
an image for final fulfillment; this slice adds no alternative acceptance path.

## Delivered Recovery Model

- One renewable lease row exists per cloud-image job. Claim after release or
  expiry increments a monotonic fencing token.
- Worker attempt IDs and `(job, stage, attempt_number)` are unique. Starts must
  be sequential, cannot overlap unresolved work, and honor durable retry time.
- An interrupted or unknown attempt can be reconciled under a newer lease. A
  superseded worker cannot renew, complete, release, or transition through its
  old fencing token.
- Worker state advancement requires the latest referenced stage attempt to
  have a final result. The job mutation, audit event, transactional outbox row,
  operation receipt, and attempt-to-transition link commit together.
- Control operation receipts provide exact replay for lease, attempt, and
  outbox mutations; changed content under an operation ID is a conflict.
- Outbox claims use owner, monotonic claim token, expiry, delivery-attempt,
  retry schedule, and dead-letter state. PostgreSQL uses `FOR UPDATE SKIP
  LOCKED`; acknowledgement with a stale owner/token is rejected.
- Unacknowledged publish claims become eligible after expiry. The event ID is
  the stable broker message identity, so delivery is deliberately at least
  once and consumer deduplication is possible.

## Verification Snapshot

- DataForge SQLite cloud-image tests: **30 passed**, covering existing PROD-01
  behavior plus lease replay/renew/release/expiry/takeover, stale fencing,
  attempt order and reconciliation, atomic attempt-transition rollback, and
  outbox retry/reclaim/ack fencing.
- DataForge PostgreSQL tests: **2 passed**. Competing state transitions, leases,
  and outbox claims each produce a single winner; takeover advances the fence.
- Alembic: full clean upgrade to `20260913_02`, downgrade to `20260913_01`,
  re-upgrade to `20260913_02`, and one current head all passed.
- NeuroForge PROD-02 gate: **14 passed**, including four retained PROD-01
  adapter cases and ten new recovery/dispatcher cases.
- NeuroForge complete focused cloud-image acceptance surface: **174 passed**.
- Static checks on the modified DataForge and NeuroForge modules pass Ruff;
  modified NeuroForge modules pass MyPy. DataForge's changed modules add no
  MyPy findings; two pre-existing findings remain in unrelated imported
  modules (`app/database.py` and `app/auth/token_rotation.py`).
- Both compiled system references rebuild and validate from their source
  chapters.

## Crash and Race Matrix

| Boundary | Proved outcome |
|---|---|
| Before/after lease mutation | injected failures roll back; exact retry is safe |
| Effect completed, attempt final, transition not committed | takeover reconciles the durable digest without re-executing the effect |
| Effect outcome unknown | attempt remains `reconciliation_required`; reconciliation precedes any state advance |
| Transition transaction interrupted | state, event, outbox, receipt, and attempt link all roll back |
| Lease expires while old worker continues | new fence wins; old fence cannot commit |
| Retry delivered before due time | no new attempt or effect |
| Cancellation wins while handler runs | post-handler terminal recheck blocks success transition |
| Publisher crashes after publish and before acknowledgement | claim expires and the same stable event ID is redelivered |
| Stale outbox acknowledgement | explicit claim conflict; current claimant remains authoritative |

## Limits and Human Gate

This source has not been deployed. It provisions no credentials, starts no
background process, selects no broker, invokes no provider SDK, downloads no
artifact, and makes no ForgeImages network call. Stage handlers and the event
publisher remain injected boundaries for later governed slices.

`PROD-02` is implemented with evidence prepared, but the human gate is still
pending. Slice 03, provider work, credentials, spend, deployment, and traffic
remain blocked until the decision owner explicitly accepts this recovery
matrix and replay evidence.
