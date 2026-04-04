# §13 — Proving-Slice Schema

Added in migration `20260404_10` (down_revision: `20260401_02`).

Two tables in the default public schema.

## ps_cloud_intake_records

Durable intake log. One row per artifact received from DataForge Local. The `idempotency_key`
UNIQUE constraint is the duplicate-detection boundary: a second submission with the same
key is reconciled without re-running validation.

| Column | Type | Notes |
|--------|------|-------|
| `intake_id` | VARCHAR(36) PK | UUID assigned at intake |
| `artifact_id` | VARCHAR(36) NOT NULL | From the incoming shared envelope |
| `artifact_family` | VARCHAR(128) NOT NULL | `source_drift_finding` or `promotion_envelope` |
| `artifact_version` | INTEGER NOT NULL | Schema version |
| `idempotency_key` | VARCHAR(64) NOT NULL UNIQUE | 64-char hex sha256; duplicate detection key |
| `produced_by_system` | VARCHAR(255) NOT NULL | Originating system (e.g. `dataforge-Local`) |
| `lineage_root_id` | VARCHAR(36) NOT NULL | Root of the artifact lineage chain |
| `trace_id` | VARCHAR(128) NOT NULL | Distributed trace identifier |
| `intake_outcome` | VARCHAR(64) NOT NULL | `accepted` / `rejected` / `duplicate_reconciled` |
| `rejection_class` | TEXT | Populated when `intake_outcome = rejected` |
| `rejection_detail` | TEXT | Human-readable rejection explanation |
| `shared_record_ref` | TEXT | Canonical `<family>:<id>:v<n>:shared` ref; set on acceptance |
| `payload_json` | JSONB NOT NULL | Family-specific payload from the artifact |
| `envelope_json` | JSONB NOT NULL | All envelope fields except `payload` |
| `received_at` | TIMESTAMPTZ NOT NULL | When the intake request was received |
| `processed_at` | TIMESTAMPTZ NOT NULL | When validation and persistence completed |

**Indexes:** `artifact_id`, `artifact_family`, `intake_outcome`, `received_at`, `lineage_root_id`

## ps_cloud_receipts

One row per receipt artifact emitted back to DataForge Local. Each `ps_cloud_intake_records`
row produces exactly one receipt row. The `receipt_artifact_id` is the `artifact_id` carried
by the `promotion_receipt` artifact returned to the caller.

| Column | Type | Notes |
|--------|------|-------|
| `receipt_id` | VARCHAR(36) PK | UUID |
| `intake_id` | VARCHAR(36) NOT NULL FK → ps_cloud_intake_records | |
| `artifact_id` | VARCHAR(36) NOT NULL | From the submitted artifact |
| `receipt_artifact_id` | VARCHAR(36) NOT NULL UNIQUE | `artifact_id` of the emitted promotion_receipt |
| `intake_outcome` | VARCHAR(64) NOT NULL | Mirrors `ps_cloud_intake_records.intake_outcome` |
| `rejection_class` | TEXT | Populated when rejected |
| `retry_allowed` | BOOLEAN NOT NULL DEFAULT FALSE | Always false for contract validation rejections |
| `outcome_summary` | TEXT | Human-readable explanation |
| `shared_record_ref` | TEXT | Canonical shared record reference |
| `emitted_at` | TIMESTAMPTZ NOT NULL | When the receipt was emitted |

**Indexes:** `artifact_id`, `intake_id`, `intake_outcome`

## Intake Decision Logic

```
POST /api/v1/proving-slice/intake

1. Family gate: only source_drift_finding and promotion_envelope admitted → 422 otherwise
2. Duplicate check: lookup idempotency_key in ps_cloud_intake_records
   → if found: return duplicate_reconciled receipt (original shared_record_ref preserved)
3. validate_artifact(artifact, strict_idempotency=True) via forge-contract-core
   → if ArtifactValidationError: persist rejected row + emit rejected receipt
4. Persist ps_cloud_intake_records (accepted) + ps_cloud_receipts
5. Return ProofReceiptArtifact (promotion_receipt family, intake_outcome=accepted)
```

The HTTP status is always `200` for domain decisions (accepted / rejected / duplicate).
`422` is reserved for unsupported families — a caller error, not a domain rejection.

## Receipt Artifact Structure

The returned receipt is a complete, schema-conforming `promotion_receipt` artifact:

- `artifact_family`: `promotion_receipt`
- `produced_by_system`: `DataForge`
- `signer_identity`: `DataForge/proving_slice_intake@proving-slice-v1`
- `payload.intake_outcome`: `accepted` | `rejected` | `duplicate_reconciled`
- `payload.shared_record_ref`: set when `accepted` or `duplicate_reconciled`
- `payload.rejection_class`: set when `rejected`
- `payload.retry_allowed`: always `false` for contract validation failures

Signature is a placeholder (`sha256:cloud-proving-slice-v1-{hash}`) — cryptographic
signing is deferred to Stage 5 key governance.

## GET /api/v1/proving-slice/receipts/by-artifact/{artifact_id}

Returns the receipt for a previously submitted artifact. DataForge Local uses this endpoint
to reconcile ambiguous sends — when the original `POST /intake` response was lost in transit,
Local can re-query by `artifact_id` to determine the true intake outcome.

Returns `404` if the `artifact_id` has never been processed.

## Test Coverage

`tests/test_proving_slice_intake.py` — **29 tests, no live PostgreSQL required** (SQLite in-memory via `tests/conftest.py`).

*Last updated: 2026-04-04*

| Class | Tests | What is verified |
|-------|-------|-----------------|
| `TestIntakeAccepted` | 8 | 200 response; receipt family/version; `accepted` outcome; shared_record_ref; `produced_by_system=DataForge`; intake + receipt rows written to DB |
| `TestIntakeDuplicate` | 3 | `duplicate_reconciled` on second submit; exactly one intake row; shared_record_ref preserved from original |
| `TestIntakeRejected` | 5 | `rejected` outcome; rejection_class present; `retry_allowed=false`; rejected row persisted; end-to-end malformed artifact without patching |
| `TestIntakeFamilyGate` | 3 | `promotion_receipt` → 422; unknown family → 422; `promotion_envelope` admitted |
| `TestReceiptLookup` | 4 | 200 after intake; artifact_id echoed; receipt family; 404 for unknown artifact_id |
| `TestIntakeAdversarial` | 6 | Replay with swapped artifact_id; tampered lineage_root_id; conflicting idempotency key; unknown producer; oversize payload; receipt-family 422 |

Adversarial tests do **not** patch `validate_artifact` — they verify the real contract-core validation pipeline fires and produces `rejected` outcomes for malformed submissions.
