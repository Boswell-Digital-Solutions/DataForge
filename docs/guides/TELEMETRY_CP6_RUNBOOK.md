# Telemetry CP6 Incident Candidate Runbook

## Boundary

DataForge stores `IncidentCandidate.v1` as derived analysis evidence. A
candidate is not an incident declaration and has no authority to repair, roll
back, notify, or promote. Every candidate requires a separate human decision.

The initial admission slice proves immutable `ForgeEvent.v1` and
`ForgeCheckResult.v1` sources by exact record ID, hash, observed time, scope,
privacy/retention/legal class, correlation, and trace. Deployment,
configuration, baseline, and unavailable trace details are named as missing
evidence. Other source kinds in the shared contract fail closed until DataForge
has a separately proved durable mapping.

Deterministic DataForge candidates record null model fields. NeuroForge
model-assisted candidates must record provider, model, prompt hash, response
hash, and run receipt provenance and remain candidate-only.

## Enablement

Apply migration `20260725_03`, prove the isolated telemetry role, and provision:

- a producer key with `telemetry:write:incident-candidates`, exact environment
  and tenant binding, and `service_name=dataforge` or `neuroforge`; and
- a Forge_Command reader key with
  `telemetry:read:incident-candidates`, exact environment and tenant binding,
  plus `telemetry:read:incident-candidates:restricted` only when classified
  candidates may be displayed.

Then independently enable:

```text
DATAFORGE_INCIDENT_CANDIDATE_WRITE_ENABLED=true
DATAFORGE_INCIDENT_CANDIDATE_READ_ENABLED=true
```

The endpoints are:

```text
POST /api/v1/telemetry/incidents/candidates
GET  /api/v1/telemetry/incidents/candidates
```

The read projection is limited to 25 candidates and 512 KiB. There are no CP6
action endpoints.

## Verification

Run focused Python tests with the exact candidate SDK:

```bash
PYTHONPATH=/path/to/forge-telemetry \
  python -m pytest -q tests/test_telemetry_incidents.py
```

Run the PostgreSQL migration, RLS/grant, constraint, backup/restore, downgrade,
and re-upgrade proof:

```bash
DATAFORGE_TEST_PYTHON=/path/to/python \
  pg_virtualenv bash scripts/prove_telemetry_cp6_postgres.sh
```

Review exact replay, fingerprint deduplication, restricted-row hiding, null
model fields for deterministic analysis, complete NeuroForge provenance, and
all hard-false action flags.

## Rollback

1. Set both CP6 switches to `false`.
2. Rotate or revoke the dedicated candidate producer and reader keys.
3. Stop any external CP6 analyzer.
4. Downgrade to `20260725_02` if runtime table access must be removed.

The downgrade revokes CP6 policies and grants while retaining the candidate
table and every row. It does not alter source evidence, restore a legacy
incident path, or authorize CP7.
