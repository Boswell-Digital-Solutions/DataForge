# Telemetry CP4 Monitoring-as-Code Runbook

## Boundary

DataForge owns durable `ForgeCheckResult.v1` and
`ForgeCheckRunReceipt.v1` evidence. ForgeAgents writes through
`POST /api/v1/telemetry/checks/evidence` using an API key bound to
`service_name=forgeagents`, the exact environment and tenant, and
`telemetry:write:checks`.

Forge_Command reads the bounded projection at
`GET /api/v1/telemetry/checks/results` using an API key bound to
`service_name=forge_command`, the exact environment and tenant, and
`telemetry:read:checks`.

Enable the routes independently:

```text
DATAFORGE_FORGE_CHECK_EVIDENCE_WRITE_ENABLED=true
DATAFORGE_FORGE_CHECK_EVIDENCE_READ_ENABLED=true
```

CP4 accepts debug evidence only. Database checks and RLS write policies keep
`slo_included`, `uptime_included`, and `baseline_included` false.

## Verification

Run the API and SQLite regression surface:

```bash
pytest -q tests/test_forge_check_evidence.py
```

Run the migration, least-privilege, RLS, constraint, rollback-retention, and
re-upgrade proof against an ephemeral PostgreSQL cluster:

```bash
DATAFORGE_TEST_PYTHON=/path/to/python \
  pg_virtualenv bash scripts/prove_telemetry_cp4_postgres.sh
```

## Rollback

1. Disable all CP4 schedules at the ForgeAgents/CI trigger.
2. Set both CP4 DataForge route switches to `false`.
3. If database runtime access must be revoked, downgrade to
   `20260724_02`.

The downgrade removes the dedicated runtime role's CP4 policies and grants.
It intentionally retains both evidence tables and every result and receipt.
Do not delete those rows during CP4 rollback. Re-upgrading recreates policies
and grants without replacing retained evidence.
