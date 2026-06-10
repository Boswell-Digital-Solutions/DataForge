# Cloud Service Security Authority (CSSA) Plan

**Subsystem:** ForgeAgents — Cloud Service Security Authority
**Date:** June 9, 2026
**Owner:** ForgeAgents maintainers
**Status:** Revised draft accepted at Phase 0 (Authority lock) — see `PHASE_0_ACCEPTANCE.md`
**Scope:** Contract law, enforcement-point law, authorization and outcome records, data-boundary
enforcement, quota reservation, rollout control, incident detection, and cross-repository
integration for ForgeCommand, NeuroForge, AuthorForge, DataForge, and DataForge-Local.

> This file is the canonical, repository-resident copy of the CSSA authority model. It is reference
> law for every subsequent implementation phase. Breaking changes to the authority model require a
> superseding revision and a fresh Phase 0 acceptance.

---

## 1. Purpose

The Cloud Service Security subsystem protects every cloud-connected action in the Forge ecosystem.

Its governing rule is:

> Every cloud action must be attributable, classified, entitled, policy-checked, quota-reserved,
> authorized, executed through a governed egress path, and reconstructable from immutable records.

The subsystem exists to prevent:

- unknown, revoked, or under-entitled principals from invoking cloud services
- cloud actions that bypass quota, policy, approvals, or data-boundary rules
- PII, secrets, customer documents, source code, or manuscripts leaving their allowed trust boundary
- NeuroForge cost-routing decisions becoming unsafe provider-routing decisions
- unsafe tool chains reaching cloud providers, storage, payments, or email
- concurrent requests overspending quota because each request observed stale quota state
- cloud activity that cannot be reconstructed later
- mutable audit records whose final state cannot be trusted
- cost spikes and abuse discovered only after provider billing
- security posture asserted in prompts, docs, memory, or UI rather than enforced by code and contracts

---

## 2. Canonical position

The Cloud Service Security subsystem consists of four bounded runtime components sharing one
contract family.

### 2.1 CloudSecurityGate

A deterministic in-process authorization engine on the hot path of every cloud-touching action.

It performs:

1. principal and executor identity resolution
2. delegation validation
3. entitlement evaluation
4. quota reservation
5. request data classification
6. provider, model, action, and tool-chain policy evaluation
7. rollout-mode evaluation
8. issuance of a single-use authorization decision

It performs no LLM inference and no autonomous reasoning.

### 2.2 GovernedEgressBroker

The only allowed execution path for registered cloud services.

It:

- consumes a valid single-use authorization
- verifies that the authorization is bound to the exact operation
- applies required redactions
- executes through an approved provider adapter or transport
- captures execution outcome metadata
- prevents direct cloud-client creation outside approved infrastructure modules

### 2.3 CloudSecurityRecorder

An immutable audit recorder.

It writes:

- `CloudActionAuthorization.v1` before execution
- `CloudActionOutcome.v1` after execution begins or terminates
- append-only integrity metadata
- durable outbox records when direct persistence is temporarily unavailable

It never mutates a previously hashed record.

### 2.4 CloudSecurityAgent

An asynchronous watchdog agent that:

- reads authorization and outcome records
- reads cost and quota ledgers
- runs deterministic anomaly detectors
- emits `SecurityIncident.v1` records to the ForgeCommand incident inbox

It has no direct enforcement authority.

---

## 3. CSSA is not

The subsystem is not:

- a prompt-based security agent
- a replacement for PolicyEngine
- a replacement for ForgeCommand approvals
- a replacement for ForgeCommand entitlement ownership
- a replacement for `forge_keys.py`
- a replacement for the LLM policy envelope
- a host firewall, network firewall, container firewall, or OS intrusion-detection system
- an incident-healing agent
- a durable owner of customer content
- a writer of lifecycle state, entitlement state, approval resolution, or rollout state

Authority comes only from:

- contracts
- validators
- authenticated policy artifacts
- immutable authorization and outcome records
- trusted runtime identity
- quota reservations
- approval records
- governed egress enforcement

Prompts, documentation, memory, or UI claims never authorize a cloud action.

---

## 4. Security invariants

The following invariants are non-negotiable.

1. Every governed cloud execution passes through GovernedEgressBroker.
2. Every execution consumes one unexpired, unused authorization.
3. Authorization is bound to the exact principal, executor, tenant, app, action, provider
   constraints, request digest, policy bundle, and expiry.
4. Every governed attempt produces one immutable authorization record.
5. Every attempt that begins execution produces one immutable terminal outcome record.
6. No previously hashed record is back-filled or mutated.
7. Unknown identity, entitlement, classification, quota state, or rollout state fails closed in
   enforcing modes.
8. R4 data never leaves its permitted trust boundary.
9. Raw quarantined customer content remains at the originating trust boundary by default.
10. Quota checks use atomic reservation, not observational counters alone.
11. The watchdog cannot directly inject allow, block, quarantine, approval, or kill-switch decisions.
12. Production builds cannot run governed cloud surfaces in unrestricted OFF mode.
13. No cloud provider SDK or outbound transport may be instantiated outside approved egress
    infrastructure.
14. ForgeCommand consumes security truth and resolves approvals, but does not become the writer of
    ForgeAgents authorization or outcome truth.

---

## 5. Trust and identity law

### 5.1 Identity model

Every governed action includes three distinct identities.

```json
{
  "principal": {
    "principal_id": "string",
    "principal_kind": "user | customer | service",
    "tenant_id": "string|null",
    "role": "user | operator | admin | service"
  },
  "executor": {
    "executor_id": "string",
    "executor_kind": "agent | service | user",
    "app_id": "string",
    "agent_type": "string|null"
  },
  "delegation": {
    "grant_id": "string|null",
    "scope": ["string"],
    "issued_at": "ISO-8601|null",
    "expires_at": "ISO-8601|null",
    "issuer": "string|null"
  }
}
```

### 5.2 Identity sources

Identity must be derived from trusted runtime context:

- verified JWT claims
- verified service credentials
- verified agent-run tokens
- validated internal service identity
- authenticated delegation grants

Request-body identity fields are descriptive only and cannot override trusted runtime identity.

### 5.3 Identity failure law

- unresolved principal → block
- unresolved executor → block
- revoked credential → block
- expired delegation → block
- delegation scope mismatch → block
- tenant mismatch → block

Initial reason codes: `PRINCIPAL_UNKNOWN`, `EXECUTOR_UNKNOWN`, `IDENTITY_REVOKED`,
`DELEGATION_MISSING`, `DELEGATION_EXPIRED`, `DELEGATION_SCOPE_DENIED`, `TENANT_MISMATCH`.

---

## 6. Enforcement architecture

```
caller
  │
  ▼
CloudActionRequest
  │
  ▼
CloudSecurityGate
  ├─ resolve principal/executor/delegation
  ├─ load authenticated policy bundle
  ├─ classify request
  ├─ evaluate entitlement
  ├─ reserve quota atomically
  ├─ evaluate provider/model/action/tool-chain rules
  ├─ apply rollout mode
  └─ issue single-use decision
  │
  ▼
CloudActionAuthorization.v1 persisted
  │
  ├─ block / quarantine / approval_required
  │      └─ no cloud execution
  │
  └─ allow / allow_redacted
         │
         ▼
GovernedEgressBroker
  ├─ consume authorization atomically
  ├─ verify request digest and binding
  ├─ apply redaction plan
  ├─ execute approved adapter/transport
  ├─ classify response metadata as required
  └─ write CloudActionOutcome.v1
         │
         ▼
DataForge durable security ledger
         │
         ▼
CloudSecurityAgent
  ├─ deterministic detectors
  └─ SecurityIncident.v1
         │
         ▼
ForgeCommand incident inbox
```

---

## 7. Enforcement-point law

### 7.1 Logical chokepoints

There are two logical authorization entry points:

1. tool execution through ToolRouter
2. LLM/provider execution through LLMManager

Both must delegate actual cloud execution to GovernedEgressBroker.

### 7.2 Physical egress law

The governed egress layer is the only module allowed to instantiate or call: `httpx`, `requests`,
`aiohttp`, `urllib`, gRPC transports, WebSocket clients, provider SDK clients, Stripe clients, cloud
storage SDKs, email provider clients, and subprocess-based network clients such as `curl`.

Approved exceptions are limited to:

- internal health probes
- local-only sockets
- test doubles
- the entitlement-policy refresh client
- the recorder's durable persistence client

Exceptions are enumerated in code and checked in CI.

### 7.3 Cloud surface registry

The static cloud registry declares: service identifier, owning adapter, allowed transports, default
risk class, permitted actions, provider/model constraints, whether approval is required by default,
whether data egress is permitted, quota bucket, and receipt strictness class.

Initial service identifiers: `neuroforge`, `openai`, `anthropic`, `dataforge`, `rake`, `stripe`,
`email`.

Unknown services fail startup registration and fail closed at runtime.

### 7.4 No-side-door verification

CI must include: prohibited import checks, prohibited client-construction checks, outbound call-site
inventory, provider SDK inventory, cloud registry coverage, a test proving each registered cloud
adapter passes through the broker, and a test proving direct network construction fails policy checks.

---

## 8. Exemption law

The exemption set is closed.

Allowed exemptions: recorder persistence writes, health/readiness/degraded-state probes, policy and
entitlement refresh, test fixtures in isolated test mode.

No actor-initiated business action is exempt.

Every exempt call emits structured metadata:

```json
{
  "gate_exempt": true,
  "exemption_code": "RECORDER_PERSISTENCE | HEALTH_PROBE | POLICY_REFRESH | TEST_ONLY"
}
```

---

## 9. Fail-closed law

In CANARY or ACTIVE enforcement:

- unknown principal or executor → block
- unknown entitlement → block
- unknown quota state → block
- quota reservation failure → block
- classifier failure → classify at highest plausible class and block or quarantine
- invalid policy signature → block
- invalid rollout state → block
- authorization persistence failure for strict actions → block
- authorization expiry → block
- authorization replay → block
- request digest mismatch → block
- egress adapter missing from registry → block
- kill switch active → block

No timeout, cache miss, recorder failure, or policy error may silently convert to allow.

---

## 10. Rollout modes

### 10.1 Modes

`OFF`, `SHADOW`, `CANARY`, `ACTIVE`.

### 10.2 Production constraints

- OFF is permitted only in tests and explicitly marked local development.
- Production governed surfaces must run at least in SHADOW.
- Global ACTIVE is illegal until both logical chokepoints, classification, quota reservation,
  approvals, immutable recording, and rollback controls are operational.

### 10.3 SHADOW

SHADOW performs: identity resolution, entitlement evaluation, classification, quota simulation,
policy evaluation, and authorization and outcome recording. SHADOW does not alter runtime behavior.
A shadow-invariance test must prove identical application behavior.

### 10.4 CANARY

Canary assignment is deterministic:

```
sha256(correlation_id + surface_id) % 100 < canary_percent
```

CANARY may be enabled per surface and per action class.

### 10.5 ACTIVE

ACTIVE enforces all decisions. Promotion requires: full registered-surface coverage, accepted latency
budgets, accepted false-block rate, zero unhandled R4 egress in the golden corpus, durable recorder
operation, and tested rollback to SHADOW.

---

## 11. Authenticated policy bundle

### 11.1 Policy bundle contents

A decision records the exact policy bundle used.

```json
{
  "bundle_id": "string",
  "issuer": "string",
  "issued_at": "ISO-8601",
  "expires_at": "ISO-8601",
  "key_id": "string",
  "entitlement_hash": "sha256:...",
  "registry_hash": "sha256:...",
  "policy_engine_hash": "sha256:...",
  "classifier_version": "string",
  "toolchain_rules_hash": "sha256:...",
  "rollout_state_hash": "sha256:...",
  "signature_algorithm": "ed25519",
  "signature": "base64"
}
```

### 11.2 Signature law

A plain SHA-256 sidecar is not a signature. Production enforcement requires: canonical payload,
issuer, key ID, expiry, anti-rollback version, and an authenticated digital signature.

Phase 2 may use a repository-trusted development key, but ACTIVE production requires ForgeCommand or
the ecosystem signing authority.

### 11.3 Entitlement ownership

- Phase 2–6: authenticated static entitlement snapshot
- Phase 7: ForgeCommand-owned entitlement API backed by Stripe and customer-plan state
- CSSA reads entitlements
- CSSA never creates, edits, upgrades, or cancels entitlements

---

## 12. Entitlement law

An entitlement grants a bounded capability.

```json
{
  "tenant_id": "string",
  "principal_id": "string",
  "app_id": "string",
  "service": "string",
  "allowed_actions": ["string"],
  "allowed_data_classes": ["R0", "R1", "R2"],
  "provider_constraints": ["string"],
  "model_constraints": ["string"],
  "quota_class": "string",
  "approval_policy": "none | conditional | required",
  "valid_from": "ISO-8601",
  "valid_until": "ISO-8601"
}
```

Missing, expired, unknown, or mismatched entitlement blocks the action.

---

## 13. Atomic quota law

Quota cannot be enforced through stale counters alone.

### 13.1 Reservation lifecycle

Every quota-governed action follows: `reserve` → `execute` → `commit` → `release_unused`.

### 13.2 Reservation contract

```json
{
  "quota_reservation_id": "uuid",
  "tenant_id": "string",
  "principal_id": "string",
  "service": "string",
  "quota_bucket": "string",
  "reserved_units": 0,
  "unit_type": "tokens | calls | usd | bytes | messages",
  "expires_at": "ISO-8601",
  "status": "reserved | committed | released | expired"
}
```

Reservations must be atomic per quota bucket.

### 13.3 Failure behavior

- reservation denied → `QUOTA_EXCEEDED`
- quota service unavailable in enforcing mode → `QUOTA_UNKNOWN`
- abandoned reservations expire automatically
- outcome records commit actual usage
- unused reservation is released
- reconciliation jobs detect leaked reservations

---

## 14. Data-boundary law

### 14.1 Classification levels

| Class | Meaning | Default cloud posture |
| --- | --- | --- |
| R0 | Public or non-sensitive | allowed within entitlement |
| R1 | Internal operational data | allowed within entitlement |
| R2 | PII, customer metadata, sensitive runtime context | redacted by default; raw egress requires explicit entitlement |
| R3 | restricted source code, customer documents, manuscripts, private artifacts | local-only by default; explicit approved path required |
| R4 | secrets, credentials, prohibited capture | never leaves the permitted trust boundary |

### 14.2 Classification sources

The classifier uses: capability-75 redaction patterns, sensitive-field names, secret-prefix
heuristics, JWT and credential patterns, structured metadata, pre-classified artifact attestations,
app-specific classification rules, and content-origin metadata.

### 14.3 Classification attestations

Large artifacts should be classified once and referenced by an attestation:

```json
{
  "artifact_ref": "string",
  "artifact_hash": "sha256:...",
  "highest_class": "R3",
  "classes_detected": ["R2", "R3"],
  "classifier_version": "string",
  "classified_at": "ISO-8601",
  "expires_at": "ISO-8601"
}
```

The gate verifies that the artifact hash still matches.

### 14.4 Redaction

Allowed transforms: `mask`, `hash`, `drop`, `tokenize`, `replace_with_reference`. Redaction occurs
before request hashing and before egress.

### 14.5 Response classification

Cloud responses are classified before: logging, persistence, chaining into another tool, and delivery
across another trust boundary.

Response classification must detect: returned secrets, sensitive provider metadata, customer
information, unsafe tool output, and newly generated credentials.

### 14.6 Streaming

Streaming outcomes use: `started`, `completed`, `failed`, `cancelled`, `partially_delivered`. The
outcome record includes delivered-byte or delivered-token counts.

---

## 15. Decision law

### 15.1 Decision enum

`allow`, `allow_redacted`, `approval_required`, `quarantine`, `block`.

### 15.2 Precedence

```
block > quarantine > approval_required > allow_redacted > allow
```

### 15.3 Policy mapping

| Existing policy action | CSSA decision |
| --- | --- |
| deny | block |
| throttle | block |
| confirm | approval_required |
| warn | allow with warning |
| allow | allow |

### 15.4 Single-use authorization

A decision: authorizes at most one execution, has a short TTL, is consumed atomically, cannot be
replayed, cannot authorize a modified request, and cannot authorize a different provider, model,
principal, tenant, executor, or action.

---

## 16. Contract family

Contracts live under `schemas/cloud_security/v1/`. Schemas use JSON Schema 2020-12. Pydantic v2
models live in `app/security/contracts.py`. Hashes use RFC 8785 canonicalization. Breaking changes
require v2.

> Phase 0 note: no schemas land at acceptance. The above is the Phase 1 target layout.

---

## 17. CloudSecurityDecision.v1

```json
{
  "schema_version": "cloud_security.decision.v1",
  "decision_id": "uuid",
  "attempt_id": "uuid",
  "operation_id": "uuid",
  "parent_attempt_id": "uuid|null",
  "correlation_id": "uuid",
  "occurred_at": "ISO-8601",
  "expires_at": "ISO-8601",
  "mode": "shadow | canary | active",

  "principal": {},
  "executor": {},
  "delegation": {},

  "app_id": "string",
  "cloud_service": "string",
  "requested_action": "string",

  "request_digest": "sha256:...",
  "classification": {
    "highest_class": "R0 | R1 | R2 | R3 | R4",
    "classes_detected": [],
    "classifier_version": "string",
    "attestation_ref": "string|null"
  },

  "entitlement_status": "valid | expired | missing | unknown",
  "quota_status": "reserved | exceeded | unknown | not_applicable",
  "quota_reservation_id": "uuid|null",

  "policy_results": [],
  "required_redactions": [],

  "decision": "allow | allow_redacted | approval_required | quarantine | block",
  "reason_codes": [],
  "approval_ref": "uuid|null",
  "quarantine_ref": "string|null",

  "provider_constraints": [],
  "model_constraints": [],
  "policy_bundle": {},
  "decision_hash": "sha256:..."
}
```

The decision is immutable.

---

## 18. CloudActionAuthorization.v1

Written before execution or terminal denial.

```json
{
  "schema_version": "cloud_security.authorization.v1",
  "authorization_id": "uuid",
  "attempt_id": "uuid",
  "decision_id": "uuid",
  "operation_id": "uuid",
  "correlation_id": "uuid",

  "principal_id": "string",
  "tenant_id": "string|null",
  "executor_id": "string",
  "app_id": "string",

  "cloud_service": "string",
  "requested_action": "string",
  "decision": "allow | allow_redacted | approval_required | quarantine | block",
  "reason_codes": [],

  "request_digest": "sha256:...",
  "redaction_count": 0,
  "quota_reservation_id": "uuid|null",

  "authorization_state": "issued | denied | approval_pending | quarantined",
  "single_use": true,
  "expires_at": "ISO-8601",
  "created_at": "ISO-8601",

  "authorization_hash": "sha256:..."
}
```

---

## 19. CloudActionOutcome.v1

Written after execution starts or terminates.

```json
{
  "schema_version": "cloud_security.outcome.v1",
  "outcome_id": "uuid",
  "attempt_id": "uuid",
  "authorization_id": "uuid",
  "operation_id": "uuid",
  "correlation_id": "uuid",

  "execution_state": "started | completed | failed | cancelled | partially_delivered",
  "provider": "string|null",
  "model": "string|null",

  "response_digest": "sha256:...|null",
  "response_classification": {
    "highest_class": "R0 | R1 | R2 | R3 | R4 | unknown",
    "classifier_version": "string"
  },

  "usage": {
    "tokens_in": 0,
    "tokens_out": 0,
    "bytes_in": 0,
    "bytes_out": 0,
    "messages": 0
  },

  "cost": {
    "currency": "USD",
    "estimated": 0.0,
    "actual": 0.0
  },

  "quota_commit_status": "committed | released | pending | failed | not_applicable",
  "duration_ms": 0,
  "error_code": "string|null",
  "created_at": "ISO-8601",

  "outcome_hash": "sha256:..."
}
```

---

## 20. SecurityIncident.v1

```json
{
  "schema_version": "cloud_security.incident.v1",
  "incident_id": "uuid",
  "detector": "cost_spike | call_rate | deny_streak | novel_provider | quota_velocity | recorder_backlog | authorization_replay | integrity_failure",
  "severity": "S0 | S1 | S2 | S3 | S4",
  "tenant_id": "string|null",
  "principal_id": "string|null",
  "executor_id": "string|null",
  "app_id": "string|null",
  "cloud_service": "string|null",

  "window": {
    "from": "ISO-8601",
    "to": "ISO-8601"
  },

  "evidence_refs": [],
  "metrics": {
    "observed": 0.0,
    "baseline": 0.0,
    "threshold": 0.0
  },

  "summary": "string",
  "status": "NEW",
  "emitted_at": "ISO-8601",
  "incident_hash": "sha256:..."
}
```

ForgeCommand owns all lifecycle transitions after `NEW`.

---

## 21. Reason codes

Initial closed set.

**Identity and delegation:** `PRINCIPAL_UNKNOWN`, `EXECUTOR_UNKNOWN`, `IDENTITY_REVOKED`,
`DELEGATION_MISSING`, `DELEGATION_EXPIRED`, `DELEGATION_SCOPE_DENIED`, `TENANT_MISMATCH`.

**Entitlement and quota:** `ENTITLEMENT_MISSING`, `ENTITLEMENT_EXPIRED`, `ENTITLEMENT_UNKNOWN`,
`QUOTA_EXCEEDED`, `QUOTA_UNKNOWN`, `QUOTA_RESERVATION_FAILED`.

**Data boundary:** `DATA_R4_PRESENT`, `DATA_R3_OUTBOUND`, `DATA_R2_REDACTION_REQUIRED`,
`DATA_CLASSIFIER_FAILED`, `RESPONSE_CLASSIFICATION_FAILED`.

**Provider and action policy:** `PROVIDER_NOT_ALLOWED`, `MODEL_NOT_ALLOWED`, `ACTION_NOT_ALLOWED`,
`TOOLCHAIN_FORBIDDEN`, `POLICY_DENY`, `POLICY_THROTTLE`.

**Execution integrity:** `AUTHORIZATION_WRITE_FAILED`, `AUTHORIZATION_EXPIRED`,
`AUTHORIZATION_REPLAY`, `REQUEST_DIGEST_MISMATCH`, `OUTCOME_WRITE_FAILED`, `POLICY_SIGNATURE_INVALID`,
`ROLLOUT_STATE_INVALID`.

**Escalation:** `APPROVAL_PENDING`, `APPROVAL_DENIED`, `QUARANTINE_REQUIRED`, `ANOMALY_HOLD`,
`KILL_SWITCH`.

New codes require a plan amendment and schema update.

---

## 22. Recorder law

### 22.1 Immutable lifecycle

Decisions, authorizations, and outcomes are immutable. Incidents are immutable at emission. No
hash-covered field is later back-filled.

### 22.2 Record cardinality

For every governed attempt: exactly one authorization record; zero outcome records when execution
never begins; exactly one terminal outcome record when execution begins. Intermediate streaming
events may use a separate append-only event stream, but do not mutate the terminal outcome contract.

### 22.3 Strict persistence

Write-before-execute is required for: R2/R3/R4-involved actions, Stripe actions, email-send actions,
approval-governed actions, quota-billed actions, customer-content actions, and external side-effect
actions.

### 22.4 Durable outbox

Async recording requires a durable outbox. Accepted implementations: (1) DataForge append-only intent
stream, (2) durable message broker, (3) narrowly scoped encrypted local spool with retention and
recovery rules. An in-memory retry queue is insufficient.

### 22.5 Recorder degradation

Recorder backlog is exposed through `/status`. Persistent backlog creates a `recorder_backlog`
incident. No strict action executes without durable authorization persistence.

---

## 23. Approval law

Approvals are owned by ForgeCommand. Every approval is bound to: principal, tenant, executor, app,
action, cloud service, request digest, classification, provider/model constraints, policy bundle,
expiry, and maximum use count.

Approval resolution does not directly execute the old decision. It permits a fresh gate evaluation.

High-risk actions use action-specific policy rather than broad service-level approval.

| Action | Default |
| --- | --- |
| stripe.payout | approval required |
| stripe.refund | conditional approval |
| stripe.webhook.read | entitlement only |
| email.bulk_send | approval or campaign policy |
| email.transactional_send | preauthorized template policy |
| email.read_metadata | entitlement only |

---

## 24. Quarantine law

### 24.1 Origin-local default

Raw customer content is quarantined at the originating trust boundary by default. ForgeCommand
receives: quarantine reference, artifact digest, classification summary, reason codes, tenant and app
identity, requested action, expiry, and release-request metadata.

### 24.2 Central raw-content prohibition

DataForge-Local must not receive raw customer manuscripts, source code, documents, or secrets unless:
the customer entitlement permits it, the operator workflow explicitly requires it, consent or support
authorization exists, encryption and retention policy are defined, and access is audited.

### 24.3 Quarantine controls

The quarantine subsystem defines: encryption owner, key authority, storage boundary, retention
period, automatic expiry, authorized readers, release workflow, deletion confirmation, and audit
trail. Quarantine release always triggers a fresh gate evaluation.

---

## 25. Provider firewall law

- Only registered providers may execute.
- Provider selection must satisfy entitlement and data-class constraints.
- Model allowlists remain owned by the LLM policy envelope.
- CSSA maps envelope terminations into security reason codes and records.
- NeuroForge remains responsible for optimization and routing preference.
- CSSA bounds the candidate set.
- A cheaper provider is never eligible when the data class, entitlement, residency, or security tier
  forbids it.
- Parent/child attempts prevent double-recording when a tool call invokes an LLM call.

---

## 26. Tool-chain law

Deterministic tool-chain rules evaluate recent governed context. Examples: secret-bearing read
followed by external egress; restricted repository read followed by unapproved model call;
customer-document access followed by email send; entitlement lookup followed by unauthorized Stripe
mutation; repeated denied provider selection; response-generated credential followed by storage or
email action.

Rules are versioned, code-reviewed data. No LLM judgment is used to determine enforcement.

---

## 27. Watchdog and incident law

### 27.1 Detectors

| Detector | Default trigger |
| --- | --- |
| cost_spike | observed cost > 3× trailing baseline |
| call_rate | > 5× baseline or absolute cap |
| deny_streak | 5 consecutive deny/quarantine results |
| novel_provider | first provider/model/action combination |
| quota_velocity | projected exhaustion within 24 hours |
| recorder_backlog | backlog exceeds age or count threshold |
| authorization_replay | any replay attempt |
| integrity_failure | hash or signature verification failure |

### 27.2 Authority boundary

The watchdog may: emit incidents, recommend policy review, create evidence summaries, and request an
anomaly hold through a persisted incident state.

The watchdog may not: directly block, directly allow, mutate entitlements, mutate rollout state,
resolve approvals, restart services, or alter lifecycle state.

The gate may enforce `ANOMALY_HOLD` only through deterministic policy consuming trusted incident state.

---

## 28. API surface

Router: `/api/v1/cloud-security`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /evaluate | advisory dry-run only; grants no execution authority |
| POST | /authorize | internal trusted surface issuing a single-use authorization |
| GET | /decisions/{decision_id} | fetch decision metadata |
| GET | /authorizations/{authorization_id} | fetch authorization |
| GET | /outcomes | query outcomes |
| GET | /incidents | list emitted incidents |
| GET | /status | modes, coverage, recorder backlog, detector state |
| POST | /quarantine/{ref}/release-request | request a fresh review path; never bypasses gate |

### 28.1 /evaluate law

`/evaluate` is advisory only. It must return:

```json
{
  "advisory": true,
  "execution_authority": false
}
```

External applications may use it for UX, but execution still requires a fresh internal authorization
consumed by the egress broker.

---

## 29. Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| CLOUD_SECURITY_MODE | shadow | global rollout mode |
| CLOUD_SECURITY_CANARY_PERCENT | 10 | canary percentage |
| CLOUD_SECURITY_POLICY_BUNDLE_PATH | unset | authenticated policy bundle |
| CLOUD_SECURITY_ENTITLEMENT_CACHE_TTL_SEC | 300 | entitlement cache TTL |
| CLOUD_SECURITY_AUTHORIZATION_TTL_SEC | 60 | single-use authorization TTL |
| CLOUD_SECURITY_RECEIPT_TARGET | dataforge | durable ledger |
| CLOUD_SECURITY_INCIDENT_TARGET | dataforge-local | ForgeCommand incident inbox |
| CLOUD_SECURITY_OUTBOX_MODE | unset | broker, DataForge stream, or encrypted spool |
| CLOUD_SECURITY_METADATA_LATENCY_P99_MS | 25 | metadata decision budget |
| CLOUD_SECURITY_SMALL_PAYLOAD_LATENCY_P99_MS | 75 | small-payload classification budget |
| CLOUD_SECURITY_ANOMALY_INTERVAL_SEC | 300 | watchdog cadence |
| CLOUD_SECURITY_COST_SPIKE_FACTOR | 3.0 | anomaly threshold |
| CLOUD_SECURITY_DENY_STREAK_THRESHOLD | 5 | deny streak |
| CLOUD_SECURITY_KILL_SWITCH | unset | block_all emergency posture |

Large-artifact classification uses attestations and does not share the metadata-only latency target.

---

## 30. Ecosystem ownership map

| Surface | CSSA responsibility | External responsibility |
| --- | --- | --- |
| ForgeCommand | emit incidents, authorization truth, approval requests, entitlement-consumption data | entitlement ownership, Stripe plan state, approval resolution, incident lifecycle, operator UI |
| NeuroForge | restrict eligible provider/model/action set by data class and entitlement | routing optimization, model ladder, cost/performance selection |
| AuthorForge | advisory evaluation, governed execution integration, local/cloud UX states | customer-facing UX, local artifact ownership, consent workflows |
| DataForge | durable append-only security ledger, quota reservation persistence | storage availability and retention implementation |
| DataForge-Local | incident inbox metadata and operator review references | review UI and local quarantine metadata |
| Sentinel | ecosystem health and healing | liveness, breakers, restart/healing decisions |

---

## 31. Revised phase plan

The implementation order prevents partial ACTIVE claims.

### Phase 0 — Authority lock

**Objective:** Accept this document and resolve all remaining open decisions.

**Gate:** no contradictions with ForgeAgents critical rules; no contradictions with telemetry trust
laws; ownership accepted by ForgeCommand, NeuroForge, AuthorForge, and DataForge maintainers;
immutable audit lifecycle accepted; quota reservation ownership accepted; quarantine boundary
accepted; signing authority identified.

**No advance:** no contract schemas land before acceptance.

### Phase 1 — Contract kernel

Build: decision/authorization/outcome/incident/quota-reservation/policy-bundle/classification-attestation
schemas, valid/invalid fixtures, Pydantic models, reason-code enums, RFC 8785 hashing tests.

**Gate:** schemas validate and reject fixtures correctly; no mutable or back-filled hash-covered
fields; contract cardinality tests pass; hash stability proven; mypy and ruff clean.

### Phase 2 — Trusted identity, policy bundle, and registry

Build: principal/executor/delegation resolver, authenticated policy bundle loader, development signing
key support, entitlement snapshot loader, cloud surface registry, prohibited transport/import checks,
outbound call-site inventory, rollout state loader, `/status`.

**Gate:** invalid signature fails closed; expired bundle fails closed; rollback-version test passes;
unknown surface fails startup; direct client construction is detected in CI; trusted runtime identity
cannot be overridden by request data.

### Phase 3 — Immutable recorder and durable outbox

Build: decision/authorization/outcome writers, DataForge persistence client, durable outbox, integrity
verification, backlog status, recorder-backlog incident source.

**Gate:** write-before-execute authorization persistence proven; process-crash recovery proven; no
duplicate authorization records; terminal outcome cardinality proven; hash verification succeeds after
read-back; persistent backlog is never silently dropped.

### Phase 4 — SHADOW at both chokepoints

Build: ToolRouter hook, LLMManager hook, GovernedEgressBroker skeleton, parent/child attempt lineage,
SHADOW decisions and records, advisory `/evaluate`.

**Gate:** 100% registered cloud-surface coverage; shadow-invariance test passes; one authorization per
attempt; no double-recording between tool and LLM layers; metadata latency budget passes; allowed
legacy behavior remains unchanged.

**No advance:** no enforcement while any registered cloud surface bypasses the broker.

### Phase 5 — Data classification and redaction in SHADOW

Build: request classifier, response classifier, R0–R4 rules, classification attestations,
mask/hash/drop/tokenize/reference transforms, large-artifact workflow, streaming-state model,
customer-content origin metadata.

**Gate:** golden corpus accepted; R4 recall is 1.0 on the known corpus; no known R4 byte sequence
reaches a provider mock; post-redaction request digest verified; response secrets are prevented from
unsafe logging; classifier failure produces fail-closed recommendation.

### Phase 6 — Atomic quota and escalation infrastructure

Build: quota reservation client, reserve/commit/release lifecycle, reservation expiry and
reconciliation, ForgeCommand approval request contract, origin-local quarantine reference contract,
action-specific approval policy, single-use authorization consumption ledger.

**Gate:** concurrent quota test cannot overspend; abandoned reservation expires; approval is bound to
exact operation; approval resolution requires fresh evaluation; raw customer content does not enter
central quarantine by default; replay tests fail closed.

### Phase 7 — CANARY enforcement

Build: enforcement of all five decisions, per-surface canary, kill switch, rollback controls, strict
persistence classes, request-digest verification, provider/action enforcement, anomaly-hold
consumption rule.

**Gate:** forced-deny matrix passes; rollback drill CANARY→SHADOW passes; false-block rate below
accepted threshold; receipt-write failure blocks strict actions; direct side-door attempts fail;
request mutation after authorization fails; authorization replay fails.

### Phase 8 — ACTIVE enforcement

**Prerequisites:** both chokepoints covered; classifier active; quota reservations active; recorder
durable; approvals active; quarantine boundaries active; signed policy bundle active; rollback tested.

**Gate:** production readiness review; all threat-model tests pass; all registered cloud services
covered; no unresolved bypass; promotion artifact signed; operator rollback runbook accepted.

### Phase 9 — Watchdog agent and incidents

Build: CloudSecurityAgent, deterministic detectors, deduplication and cooldown, incident emission,
incident read API, integrity-failure detector, authorization-replay detector.

**Gate:** every detector fires exactly at threshold; no incident storm under repeated evidence;
watchdog failure does not affect gate operation; watchdog cannot directly inject a decision; incident
evidence contains references, not raw payloads.

### Phase 10 — Business control-plane integration

Build: ForgeCommand entitlement API v1, Stripe-linked plan and quota integration, cached entitlement
client, ForgeCommand approval UI, incident lifecycle UI, quarantine metadata review UI, AuthorForge
integration guide, NeuroForge data-class-aware route filtering.

**Gate:** cross-repo contract tests pass; Stripe entitlement change alters enforcement predictably;
quota usage appears with lineage; ForgeCommand consumes but does not rewrite authorization truth;
AuthorForge preserves customer-local quarantine; NeuroForge routing cannot select a forbidden
provider.

---

## 32. Verification matrix

| Phase | Proves |
| --- | --- |
| 1 | contracts are immutable law |
| 2 | identity, registry, and policies are authenticated |
| 3 | audit truth survives failure |
| 4 | all cloud paths are observed without interference |
| 5 | the data boundary is real |
| 6 | quotas and escalation are race-safe and bound |
| 7 | enforcement is reversible and narrow |
| 8 | full production enforcement is complete |
| 9 | watchdog is useful but powerless |
| 10 | business control plane integrates without stealing authority |

---

## 33. Planned file inventory

| File | Phase | Responsibility |
| --- | --- | --- |
| schemas/cloud_security/v1/cloud_security_decision.schema.json | 1 | decision |
| schemas/cloud_security/v1/cloud_action_authorization.schema.json | 1 | pre-execution authorization |
| schemas/cloud_security/v1/cloud_action_outcome.schema.json | 1 | terminal outcome |
| schemas/cloud_security/v1/security_incident.schema.json | 1 | incident |
| schemas/cloud_security/v1/quota_reservation.schema.json | 1 | quota reservation |
| schemas/cloud_security/v1/policy_bundle.schema.json | 1 | authenticated policy bundle |
| schemas/cloud_security/v1/classification_attestation.schema.json | 1 | artifact classification |
| app/security/contracts.py | 1 | Pydantic models |
| app/security/identity.py | 2 | principal/executor/delegation |
| app/security/policy_bundle.py | 2 | signature and expiry validation |
| app/security/registry.py | 2 | cloud surface registry |
| app/security/transport_policy.py | 2 | prohibited-client checks |
| app/security/recorder.py | 3 | immutable recorder |
| app/security/outbox.py | 3 | durable outbox |
| app/security/gate.py | 4 | pure decision core |
| app/security/egress.py | 4 | governed egress broker |
| app/security/tool_hook.py | 4 | ToolRouter integration |
| app/security/llm_hook.py | 4 | LLMManager integration |
| app/security/classifier.py | 5 | request/response classifier |
| app/security/redaction.py | 5 | transforms |
| app/security/quotas.py | 6 | reservation lifecycle |
| app/security/escalation.py | 6 | approval and quarantine references |
| app/security/rollout.py | 7 | mode and canary |
| app/api/cloud_security.py | 4–9 | API surface |
| app/agents/cloud_security/agent.py | 9 | watchdog |
| app/agents/cloud_security/detectors.py | 9 | deterministic detectors |
| tests/contracts/test_cloud_security_contracts.py | 1 | schema tests |
| tests/security/test_no_side_door.py | 2–4 | egress enforcement |
| tests/security/test_shadow_invariance.py | 4 | behavior invariance |
| tests/security/test_data_boundary.py | 5 | R-class enforcement |
| tests/security/test_quota_races.py | 6 | atomic reservation |
| tests/security/test_authorization_replay.py | 6–7 | single-use law |
| docs/cloud-security/CSSA_MODULE_SPEC.md | 9 | implemented subsystem spec |

---

## 34. Accepted design decisions

1. Entitlement v0 uses an authenticated signed snapshot, not an unsigned hash sidecar.
2. Audit records are split into immutable authorization and outcome records.
3. Global ACTIVE occurs only after both chokepoints, classification, quota reservation, approvals, and
   durable recording exist.
4. `/evaluate` is advisory and grants no authority.
5. All physical cloud egress passes through GovernedEgressBroker.
6. Identity distinguishes principal, executor, and delegation.
7. Quotas use atomic reservations.
8. Customer quarantine is origin-local by default.
9. ForgeCommand receives a dedicated incident event class.
10. Production OFF mode is prohibited for governed cloud surfaces.
11. Async recording requires a durable outbox.
12. Policy state uses authenticated signatures and explicit component hashes.

---

## 35. Remaining open decisions

See `OPEN_DECISIONS.md` for the tracked status and Phase 0 resolutions of these items.

1. Signing authority.
2. Durable outbox implementation.
3. Quota authority.
4. Local quarantine implementation.
5. Response-classification timing.
6. Regional and residency rules.
7. Key rotation.

These decisions must be resolved before their corresponding implementation phases, but they do not
block acceptance of the overall authority model.

---

## 36. Final rule

A future cloud-security proposal is not ready for implementation review unless it identifies: the
contract it changes, the authority owner it affects, the enforcement point it modifies, the trust
boundary it crosses, the immutable records it produces, the rollback behavior, and the phase gate that
proves it safe.

No cloud-security capability is accepted because it appears intelligent. It is accepted only when it is
deterministic, attributable, bounded, testable, reversible, and reconstructable.
