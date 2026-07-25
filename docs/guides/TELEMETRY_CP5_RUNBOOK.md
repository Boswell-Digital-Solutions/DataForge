# Telemetry CP5 Adaptive-Retention Runbook

## Boundary

DataForge owns durable CP5 retention decisions, routine aggregates, and
`TelemetryDerivationReceipt.v1` records. Classification uses the sink-owned
`received_at` timestamp and the hash-bound policy at
`app/models/contracts/telemetry_retention_policy.v1.json`.

CP5 is shadow-only:

- routine successes receive `aggregate_then_delete` projections;
- sampled normal traces receive short `retain` projections;
- slow checks, failures, and governed evidence receive longer `retain`
  projections;
- legal-hold evidence receives a non-expiring `legal_hold` projection; and
- every decision and aggregate has a derivation receipt explaining policy,
  window, sampling, sources, output digest, reason, privacy/legal classes, and
  uncertainty.

No CP5 path updates or deletes source evidence. `deletion_enabled`,
`decision.applied`, and `source_overwritten` remain false.

Forge_Command reads the bounded projection at:

```text
GET /api/v1/telemetry/retention/shadow
```

The caller key must be bound to `service_name=forge_command`, the exact
environment and tenant, and `telemetry:read:retention`. Classified rows also
require `telemetry:read:retention:restricted`.

Enable only the read projection:

```text
DATAFORGE_TELEMETRY_RETENTION_SHADOW_READ_ENABLED=true
```

There is no retention-policy write, schedule, apply, or deletion API in CP5.

## Verification

Run the focused DataForge tests with the candidate SDK on `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/forge-telemetry:. \
  python -m pytest -q tests/test_telemetry_retention.py
```

Run the migration, RLS/grant, constraint, backup/restore, disposable deletion,
post-deletion restore, rollback-retention, and re-upgrade proof against an
ephemeral PostgreSQL cluster:

```bash
DATAFORGE_TEST_PYTHON=/path/to/python \
  pg_virtualenv bash scripts/prove_telemetry_cp5_postgres.sh
```

The deletion rehearsal runs only in a disposable database restored from the
proof backup. It never enables CP5 deletion in DataForge.

## Shadow Review

Before any future non-shadow policy is proposed, review:

1. decision counts and reason-code distribution;
2. one receipt for every decision and every aggregate;
3. sampled-normal-trace seven-day projections;
4. slow/failure/governed/legal-hold classification;
5. `received_at` window and projected-deletion calculations;
6. restricted-row redaction and exact caller scope;
7. backup/restore and disposable deletion proof output; and
8. confirmation that source digests and source records were not rewritten.

Deletion and privacy defaults require an explicit human decision. CP5
acceptance does not authorize CP6 and does not authorize applying deletions.

## Rollback

1. Set `DATAFORGE_TELEMETRY_RETENTION_SHADOW_READ_ENABLED=false`.
2. Remove or rotate the Forge_Command CP5 read key.
3. Stop any external shadow evaluator using this policy.
4. Downgrade to `20260725_01` only if runtime table access must be revoked.

The downgrade removes the CP5 runtime role policies and grants. It intentionally
retains all three CP5 tables and every derivation, decision, and aggregate row.
Do not rewrite or delete source evidence during rollback. Re-upgrading restores
the policies and grants without replacing retained evidence.
