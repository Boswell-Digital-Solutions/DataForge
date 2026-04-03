# §9 — Error Handling, Lifecycle & Access Control

## BugCheck Finding Lifecycle State Machine

The lifecycle state machine is the most critical behavioral contract DataForge enforces. It is implemented at the API layer, not as advisory logic.

### States

| State | Description |
|-------|-------------|
| `NEW` | Finding just ingested, no human review yet |
| `TRIAGED` | Reviewed and classified by a human |
| `FIX_PROPOSED` | MAID/XAI has generated a fix proposal |
| `APPROVED` | Fix approved by authorized user |
| `APPLIED` | Fix has been applied to the codebase |
| `VERIFIED` | Applied fix confirmed correct by re-run |
| `CLOSED` | Finding resolved and archived |
| `DISMISSED` | Finding explicitly dismissed (requires reason + scope + expiration) |

### Valid Transitions

```
NEW ──────────────────────────────────────────────► DISMISSED
 │
 └──► TRIAGED ──────────────────────────────────────► DISMISSED
          │
          └──► FIX_PROPOSED ──────────────────────────► DISMISSED
                    │
                    └──► APPROVED
                              │
                              └──► APPLIED
                                       │
                                       └──► VERIFIED
                                                │
                                                └──► CLOSED
```

**DISMISSED** is reachable from any non-terminal state. `CLOSED` and `DISMISSED` are terminal states — no transitions out.

### Invalid Transitions (return 409 Conflict)

Any transition not in the valid set above returns `409 Conflict`. Examples:

| Attempted Transition | Response |
|---------------------|---------|
| `NEW → APPROVED` | 409 — must pass through TRIAGED |
| `NEW → APPLIED` | 409 — multiple steps skipped |
| `VERIFIED → NEW` | 409 — backward transition |
| `CLOSED → TRIAGED` | 409 — terminal state |
| `DISMISSED → FIX_PROPOSED` | 409 — terminal state |
| `APPLIED → TRIAGED` | 409 — backward transition |

### DISMISSED Requirements

The `DISMISSED` state requires three additional fields in the transition payload:

```json
{
  "to_state": "DISMISSED",
  "reason": "false_positive — test fixture intentionally triggers this pattern",
  "scope": "file",
  "expiration": "2026-12-31T00:00:00Z"
}
```

| Field | Type | Constraint |
|-------|------|-----------|
| `reason` | str | Required, minimum 10 characters |
| `scope` | enum | `file` \| `function` \| `project` \| `global` |
| `expiration` | datetime | Required, must be future date |

Dismissals without these fields return `422 Unprocessable Entity`.

### Run Immutability After Finalization

When a run transitions to `status = "finalized"`:

- All subsequent `POST /api/v1/bugcheck/runs/{run_id}/findings` return **409 Conflict**
- All subsequent `POST /api/v1/bugcheck/runs/{run_id}/progress` return **409 Conflict**
- The run record becomes read-only
- Existing findings retain their lifecycle states and continue to accept transitions

This is enforced in the finding ingestion endpoint:

```python
run = db.get(BugCheckRunModel, run_id)
if run is None:
    raise HTTPException(404, "Run not found")
if run.status == "finalized":
    raise HTTPException(409, "Run is finalized; new findings rejected")
```

---

## HTTP Status Code Reference

| Code | Meaning in DataForge Context |
|------|------------------------------|
| `200 OK` | Successful GET, PATCH |
| `201 Created` | Successful POST (resource created) |
| `204 No Content` | Successful DELETE |
| `400 Bad Request` | Malformed request body (JSON parse error) |
| `401 Unauthorized` | Missing or invalid auth token |
| `403 Forbidden` | Valid auth, but insufficient scope/permissions |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Invalid lifecycle transition, run finalized, duplicate fingerprint |
| `422 Unprocessable Entity` | Valid JSON but fails schema validation (Pydantic) |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unexpected server fault |
| `503 Service Unavailable` | PostgreSQL or Redis unavailable |

---

## Access Control Enforcement

### Token Validation Flow

Every protected endpoint runs this validation before business logic:

```
Request arrives
    │
    ├── Extract token from Authorization header
    │   (Bearer {token} or X-API-Key {key} or X-Run-Token {token})
    │
    ├── Validate signature (HMAC or JWT)
    │
    ├── Check expiry
    │
    ├── Check token type matches endpoint requirements
    │   (run_token ≠ user_token ≠ API key ≠ admin JWT)
    │
    ├── For run_token: validate run_id claim matches path parameter
    │
    └── For run_token: validate nonce (not replayed)
```

Any failure at any step returns 401 or 403 with no further processing.

### Scope Violations

| Attempted Action | Actor | Response |
|-----------------|-------|---------|
| BugCheck writes lifecycle transition | BugCheck (run_token) | 403 |
| VibeForge writes finding | VibeForge (user_token) | 403 |
| BugCheck finalizes run | BugCheck (run_token) | 403 |
| XAI writes finding | XAI (run_token) | 403 (enrichment endpoint only) |
| Any service rotates tokens | Non-admin | 403 |

These are **system faults**, not user errors. They are logged as security events in the audit log with the actor's token claims and the attempted operation.

---

## Duplicate Fingerprint Handling

Every finding has a `fingerprint` field that is stable across runs for the same logical issue. Fingerprints are computed by the BugCheck agent:

```python
# Default fingerprint
fingerprint = sha256(f"{category}:{rule_id}:{file_path}:{line_range}:{normalized_message}")

# Category-specific fingerprints
# API Contract Drift:
fingerprint = sha256(f"{service}:{schema_path}:{field_name}:{change_type}")
# Dependency CVE:
fingerprint = sha256(f"{package_name}:{version_range}:{cve_id}")
# Flaky Test:
fingerprint = sha256(f"{test_file}:{test_name}:{failure_signature}")
```

On ingestion, DataForge checks for an existing finding with the same `fingerprint` in any prior run for the same service. If found, it associates the new finding with the existing record via `correlation_id` rather than creating a duplicate. This enables trending and deduplication across runs.

---

## Error Response Format

All DataForge error responses follow FastAPI's standard format:

```json
{
  "detail": "Human-readable description of the error"
}
```

For validation errors (422), the format includes field-level detail:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "reason"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

---

## Graceful Degradation Policy

DataForge does not degrade silently. When dependencies are unavailable:

| Dependency | Behavior |
|-----------|---------|
| PostgreSQL down | All endpoints return 503; liveness probe returns 503 |
| Redis down | Cache reads degrade to DB or miss; authority-adjacent checks fall back to DB; rate limiting and token revocation fail closed (deny) |
| Embedding provider down | Document write returns 202 (accepted); chunking queued for retry; search returns existing results without new document |
| Celery down | Async tasks queued in DLQ; synchronous path used as fallback where possible |

**Safe fail-open exceptions:** None for authority or access control. Cache may degrade performance, but it never widens permissions or bypasses revocation/rate-limit decisions.

---

## Compliance Deletion (GDPR / CCPA)

Historical docs described a multi-step erasure workflow here. The current canonical audit does
not treat that older flow or its former dedicated test file as verified repo truth. Any GDPR
or CCPA deletion contract should be re-documented only after the live implementation and test
surface are re-audited.
