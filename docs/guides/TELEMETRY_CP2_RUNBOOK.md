# Canonical Telemetry CP2 Operations Runbook

## Scope

This runbook covers only the authorized CP2 bounded-recovery and database
blast-radius controls. It does not authorize collector ingress, CP3
correlation, legacy route restoration, or a production rollout.

## Prerequisites

1. Apply Alembic revision `20260724_02`. It creates the fixed NOLOGIN,
   non-superuser, non-`BYPASSRLS` group role
   `dataforge_telemetry_ingest`, grants only schema usage, `SELECT`/`INSERT` on
   `forge_events_v1`, and `EXECUTE` on the atomic ingest and table-constraint
   validation functions, then adds role-scoped RLS policies.
2. As a database administrator, create a distinct LOGIN role for the DataForge
   runtime. Do not reuse the business-pool role:

   ```sql
   CREATE ROLE dataforge_telemetry_runtime
       LOGIN
       NOSUPERUSER
       NOCREATEDB
       NOCREATEROLE
       NOREPLICATION
       NOBYPASSRLS
       CONNECTION LIMIT 4;
   GRANT dataforge_telemetry_ingest TO dataforge_telemetry_runtime;
   ```

3. Set the login password through the platform secret manager or an
   interactive administrator command. Never place it in repository files,
   shell history, logs, or evidence.
4. Set `DATAFORGE_TELEMETRY_DATABASE_URL` to that login's PostgreSQL URL.
   DataForge fails closed if it is missing, uses the business username, lacks
   group membership, is privileged, bypasses RLS, or cannot establish the
   exact `dataforge-telemetry` application name.

## Fixed pilot budget

Per DataForge process:

| Boundary | CP2 pilot value |
| --- | ---: |
| Telemetry DB pool | 2 |
| DB overflow | 0 |
| Pool checkout timeout | 2 s |
| Connect timeout | 3 s |
| Statement timeout | 2,000 ms |
| Lock timeout | 500 ms |
| Idle-in-transaction timeout | 5,000 ms |
| Ingest rate | 20 events/s |
| Ingest burst | 40 events |
| SQLite spool | 512 events / 32 MiB |
| Drain batch | 4 |
| Delivery attempts | 5 |
| Retry backoff | 1–30 s |
| Circuit | 3 failures / 15 s open |
| Inflight lease | 30 s |
| Shutdown bound | 15 s |

`/health/telemetry` exposes these non-secret bounds, pool checkout/overflow
state, role-preflight state, queue age/count/bytes/states, circuit state, and
delivery counters.

## Enablement sequence

1. Keep `DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=false`.
2. Apply the migration and create/grant the dedicated login.
3. Configure `DATAFORGE_TELEMETRY_DATABASE_URL`.
4. Restart DataForge so database identity and pool settings cannot drift
   in-process.
5. Verify `/health/telemetry` reports the isolated pool as configured with two
   connections and zero overflow.
6. Enable `DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=true`.
7. Submit an authenticated fixture and verify `inserted`, then replay the same
   event and verify `exact_replay`.
8. For the producer pilot, create a unique directory owned by the DataForge OS
   user with mode `0700`, set `DATAFORGE_TELEMETRY_SPOOL_PATH` to a file beneath
   it, and restart.

Queue admission is only `accepted_not_persisted`. Do not report persistence
until the linked downstream receipt says `inserted` or `exact_replay`.

## Indeterminate review

Acknowledgement loss and expired inflight leases remain `indeterminate`.
DataForge never retries them automatically. An operator must:

1. identify the event by UUID and digest without exposing event content;
2. query the canonical sink for the same identity;
3. record whether the event is absent, exact, conflicting, or unknown; and
4. call the SDK's
   `retry_indeterminate(event_id, allow_duplicate_risk=True)` only after
   explicitly accepting the remaining duplicate risk.

## Rollback

Rollback is evidence-preserving:

1. Unset `DATAFORGE_TELEMETRY_SPOOL_PATH` and restart to return the producer to
   CP1b direct canonical HTTP.
2. If the sink must stop, set
   `DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=false`. This rejects new writes and
   does not delete canonical rows.
3. Keep the spool file private and intact while any queued, quarantined, or
   indeterminate row remains. Do not copy it into evidence.
4. If database access itself must be withdrawn, downgrade only revision
   `20260724_02` after disabling writes. Its downgrade removes RLS policies and
   revokes the group role's grants; it does not delete telemetry evidence or
   drop externally provisioned login roles.

Never restore the pre-v1 batch route, direct database producer, legacy
dependency, examples, or dual-write path.
