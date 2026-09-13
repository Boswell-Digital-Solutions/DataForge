# BDS-DF-RF-001 — Receipt-to-Finding Knowledge Spine v0.1 — WP-00 Source Lock and Board Review 1 Packet

**Plan ID:** `BDS-DF-RF-001`
**Title:** Receipt-to-Finding Knowledge Spine v0.1
**Canonical owner (proposed):** `Boswell-Digital-Solutions/DataForge`
**Scope:** cross_repository
**Lifecycle:** `proposed`
**Current authority:** Documentation placement and registration only
**Runtime authority:** None
**Date:** 2026-09-13

## 0. Why this plan exists

`BDS-RMCP-FC-GIR-v0.1` (Render/Forge_Command Governed Incident Repair, Amendments 002 and 003) names a `BDS-DF-RF-001` "Receipt-to-Finding Knowledge Spine v0.1" as the required DataForge storage/envelope mapping before any evidence receipt from that plan can move past `queued` to `persisted`, and before any receipt can become a qualified finding rather than a candidate. As of 2026-09-13, `A3-GATE-00B` in that plan is blocked solely on this dependency. A second plan, `BDS-FPRS-v0.1` (Forge PR Steward), independently names `BDS-DF-RF-001` as its authority for "source-locked intent, forecast, reconciliation, findings and human verdict." **Neither plan can cite an actual `BDS-DF-RF-001` document — it has never been authored or registered.** The 2026-09-13 Board ruling on `BDS-RMCP-FC-GIR-v0.1` was to author it as its own plan. This document is that authoring's WP-00.

## 1. Source lock

| Repository | Default branch | Locked commit | Role in this plan |
|---|---|---|---|
| `Boswell-Digital-Solutions/DataForge` | `master` | `3bc6c501d8793ba716bec4f4ed549583fa5ac9dc` | Proposed canonical owner; durable storage authority; hosts the existing `llm-intel/pending-records` intake this plan's design leans on |
| `Boswell-Digital-Solutions/Forge-Agents` | `master` | `2eb8a9128ad55b775f7ddd4d23cdd22aac77c883` | Owns `Finding` (BugCheck) — the adjacent, pre-existing authority this plan must not duplicate or collide with |
| `Boswell-Digital-Solutions/forge_contract_core` | `master` | `7b4b027a3563e1248f231be16930426b8ee075e1` | Candidate schema-admission authority for any new receipt/evidence-link/finding-candidate/disposition contract |
| `Boswell-Digital-Solutions/forge-telemetry` | `main` | `e548757f006a58ac4e6be3afc29ae175ccfc677d` | Owns `TelemetryEmitReceipt.v1` and the `queued`/`persisted` delivery-outcome semantics this plan's receipts must be consistent with |

Any drift from these heads reopens the affected finding below before implementation planning proceeds.

## 2. Verified current-state architecture (code-verified 2026-09-13, not assumed)

### 2.1 "Finding" already has a live owner, with a second dormant shape in flight

BugCheck's `Finding` model (`Forge-Agents/app/agents/bugcheck/schemas/models.py:387-409`) is fully wired end-to-end today: `finding_id, run_id, fingerprint, correlation_id, severity, category, confidence, title, description, location, lifecycle_state, autofix_available, provenance, rule_id, suggested_fix, related_docs, tags, first_seen_run_id, created_at, updated_at`. Lifecycle (`LifecycleState`, `models.py:54-64`) is forward-only: `NEW → TRIAGED → FIX_PROPOSED → APPROVED → APPLIED → VERIFIED → CLOSED`, plus `DISMISSED`. Per this ecosystem's own authority table, BugCheck may write findings but never their lifecycle transitions — only Forge Command does.

This model persists to DataForge live, today: `Forge-Agents/app/services/dataforge_client.py:320-365` POSTs to `/api/v1/bugcheck/runs/{run_id}/findings`; `DataForge/app/api/bugcheck_router.py:272-340` implements the endpoint, enforcing "CRITICAL RULE #6" — a `409 RUN_ALREADY_FINALIZED` once the parent run is finalized (verified directly, `bugcheck_router.py:295-301`). This is a real, working producer→consumer path, not aspirational documentation.

A second, contract-admitted-but-dormant shape also exists: `forge_contract_core/contracts/families/bugcheck_finding/bugcheck_finding.v1.schema.json` (RFC-BC-01) — a *different* field set (`check_receipt_id, repository_id, commit_sha, rule_id, category, severity, confidence_percent, path, symbol, start_line, end_line, fingerprint_version, fingerprint, evidence_refs, source_attribution, classification`), admitted per `forge_contract_core/doc/system/10_service-contract/02-admitted-families.md` but with producer/consumer marked `(deferred)` pending BugCheck's own BC-30 (DataForge persistence) and BC-40 (Forge Command lifecycle cutover) slices.

**Consequence for this plan:** BDS-DF-RF-001 must not create a third "finding" shape. See §4.

### 2.2 Receipt/evidence contracts already admitted in `forge_contract_core` (verbatim required fields, verified 2026-09-13)

| Contract | Required fields |
|---|---|
| `TelemetryEmitReceipt.v1` | `schema_version, receipt_id, event_id, event_digest, attempt_id, previous_receipt_id, route_class, route_obligation_ref, route_satisfied, attempted_at, observed_at, sink_results, aggregate_status` |
| `ForgeCheckRunReceipt.v1` | `schema_version, receipt_id, run_id, result_id, check_id, definition_sha256, source, runner, trigger, evaluation_mode, status, started_at, observed_at, slo, cost, kill_switch, evidence_refs` |
| `ForgeCheck.v1` | `schema_version, check_id, revision, owner, environment, source, kind, evaluation_mode, schedule, timeout_ms, assertion, privacy_class, slo, cost, safety, enabled, kill_switch_ref, labels` (marked `PROPOSED for CP4`) |
| `ForgeCheckResult.v1` | `schema_version, result_id, run_id, check_id, check_revision, definition_sha256, environment, evaluation_mode, status, reason_code, started_at, finished_at, duration_ms, assertion_passed, slo, cost_units_observed, privacy_class, correlation_id, trace_id` |
| `IncidentCandidate.v1` | `schema_version, candidate_id, created_at, environment, tenant_ref, correlation_id, trace_ids, window, source_evidence, suspected_cause, alternatives, confidence, uncertainty, missing_evidence, deduplication, analysis_provenance, privacy_class, authority` |
| `ServiceHealthEnvelope.v1` | `schema_version, status, version` (required); full: `+ service_id, timestamp, authority_domain, route_fallback` |

`IssueQualificationReceipt.v1` — named as a reuse candidate in `BDS-RMCP-FC-GIR-v0.1` Amendment 002 §6 — **does not exist in any searched repository** (confirmed via direct grep across `forge_contract_core`, `Forge-Agents`, `DataForge`, `forge-telemetry`, 2026-09-13). This appears to be a Drive-authored reference to a contract that was never implemented. `BDS-RMCP-FC-GIR-v0.1` should be corrected separately; this plan does not assume that contract exists.

`telemetry_emit_receipt` producers: `DataForge, ForgeAgents, NeuroForge, Rake`; consumers: `DataForge, Forge_Command` (evidence-only — admission does not itself activate runtime emission or release promotion, per `02-admitted-families.md`).

### 2.3 DataForge already runs a structurally-similar intake pipeline — a reusable pattern, not a reusable endpoint

The `llm-intel/pending-records` flow (`DataForge/app/api/llm_intel_pending_records_router.py`, mounted `app/main.py:55,352`) already models almost exactly this plan's target shape:

```
receipt → extracted claim → pending candidate → drift report → promotion decision → promoted record
```

via `LLMIntelReceiptRecord, LLMIntelSourceFingerprintRecord, LLMIntelExtractedClaimRecord, LLMIntelPendingCandidateRecord, LLMIntelDriftReportRecord, LLMIntelReplayManifestRecord, LLMIntelPromotionDecisionRecord, LLMIntelPromotedRecord, LLMIntelSupersessionChainRecord` (`llm_intel_pending_records_models.py`). Ingest is family-tagged and idempotent (`POST /api/v1/llm-intel/pending-records`, `LLMIntelPendingRecordIngestRequest{record_family, run_id, payload}` → response includes `storage_status: "stored"|"duplicate"`, `promotion_application_allowed: false`).

**This is a pattern to generalize, not an endpoint to call.** The storage/service/promotion logic (`app/services/llm_intel_pending_records.py`, `llm_intel_promotion_application.py`) is currently LLM-intel-specific. Reuse means extracting the generic shape (receipt → evidence-link → candidate → disposition, with a family discriminator) into something `BDS-RMCP-FC-GIR-v0.1`'s Render/CI receipts can also use, rather than building an unrelated third intake pipeline from scratch.

### 2.4 `queued` vs. `persisted` is already a real, defined distinction

`forge-telemetry/forge_telemetry/receipts.py:44-50` defines `SinkStatus` (`PERSISTED` vs. `QUEUED`) as a per-attempt delivery-outcome computed by the transport layer itself, not a separate side channel: `queued` means durably spooled locally awaiting drain; `persisted` means DataForge acknowledged receipt. DataForge's `telemetry_router` (`app/main.py:324`, "Canonical `ForgeEvent.v1` capability and ingest") is mounted and receiving, though `BDS-FT-NATIVE-OBS-001`'s own next-action ("Deploy production DataForge writer") suggests the production write path isn't yet confirmed live end-to-end.

## 3. Related plans (registry-checked, no hidden duplicate found)

- `BDS-RMCP-FC-GIR-v0.1` (`Forge_Command`) — the originating dependency; `A3-GATE-00B` blocked on this plan's existence.
- `BDS-FPRS-v0.1` ("Forge PR Steward") — independently cites `BDS-DF-RF-001` as authority for "source-locked intent, forecast, reconciliation, findings and human verdict." A second live consumer.
- `BDS-FORGE-OCX-v0.1` ("Forge Observability Comprehension Experience") — plans to "pin telemetry and receipt contracts" as part of its own CP1. Adjacent, not overlapping: a comprehension/UX layer over existing contracts, not a new persistence authority.
- No plan in the canonical registry is already titled around "receipt-to-finding," "finding-candidate," or "disposition" under a different name.

## 4. Proposed design boundary (the load-bearing decision this plan must get right)

`BDS-DF-RF-001`'s "finding-candidate" must be **explicitly pre-BugCheck-finding** — what a Render/GitHub-CI evidence receipt becomes before it is ever eligible to enter BugCheck's qualified-finding lifecycle. It is not a replacement for, nor a parallel path to, `Finding`/`bugcheck_finding.v1`. Both `BDS-RMCP-FC-GIR-v0.1` source documents already encode this framing correctly (Amendment 003: "a finding remains a *candidate* until the separate `BDS-DF-RF-001` lifecycle qualifies it"; `A3-WP00B`: "durable storage and finding qualification remain separate from release/deployment truth") — this plan's job is to make that framing concrete and code-verifiable, not to invent a competing one.

Two boundary options for Board Review to choose between:

- **Option A — terminal candidate.** `BDS-DF-RF-001` finding-candidates are a DataForge-owned record type that never becomes a `bugcheck_finding`. Simpler; avoids any coupling to BugCheck's still-partially-dormant BC-30/BC-40 work; but means Render/CI evidence never joins BugCheck's own triage/lifecycle tooling.
- **Option B — narrow promotion hook.** `BDS-DF-RF-001` finding-candidates can be explicitly promoted into `bugcheck_finding.v1` once BC-30/BC-40 land, via a defined (not ad hoc) hand-off contract. More capable; couples this plan's timeline to BugCheck's, and requires BC-30/BC-40's still-deferred producer/consumer wiring to actually exist before the hook can be exercised.

## 5. Non-goals and prohibited authority (same discipline as `BDS-RMCP-FC-GIR-v0.1`)

This plan does not authorize: credentials, provider connections, live probes, schema publication or admission, database/storage migrations, runtime code, API routes, repository mutation beyond separately authorized documentation placement, deployment, rollback, or any change to BugCheck's existing `Finding`/`bugcheck_finding.v1` machinery. It does not retroactively grant `BDS-RMCP-FC-GIR-v0.1` Phase 1 authority, and it does not close `BDS-RMCP-FC-GIR-v0.1`'s `A3-GATE-00B` item 5 by itself — that closes only once this plan exists, is registered, and its storage/envelope mapping is admitted.

## 6. Open decisions for Board Review 1

| ID | Decision | Why it needs a ruling |
|---|---|---|
| `OD-01` | Canonical owner: `DataForge` (proposed here) or `forge_contract_core` (schema-admission authority) or co-owned? | Determines where this plan's canonical home and future PRs live. |
| `OD-02` | Boundary option A (terminal candidate) or B (promotion hook into `bugcheck_finding.v1`)? | Determines whether this plan's timeline couples to BugCheck's BC-30/BC-40. |
| `OD-03` | Generalize the existing `llm-intel/pending-records` pipeline, or build a separate family-generic intake from scratch? | Determines implementation cost and risk of destabilizing the working LLM-intel flow. |
| `OD-04` | Correct `BDS-RMCP-FC-GIR-v0.1` Amendment 002 §6's reference to a nonexistent `IssueQualificationReceipt.v1`? | That plan should not keep citing a contract that was never built. |

## 7. Smallest authorized next instruction

Authorize documentation-only `WP-01` to: draft the two-family contract candidate this plan needs (receipt, evidence-link, finding-candidate, disposition), scoped by the Board's ruling on OD-01/OD-02/OD-03 above; produce a source-lock refresh if any of the four repositories drift; and register this plan in both DataForge's local `docs/plans/registry.json` and the canonical ecosystem plan registry.

Do not authorize schema publication, admission, runtime implementation, database changes, or any BugCheck-side modification.

## Gate for this document

- [x] Every architecture claim above is a direct code citation (file:line), verified independently, not paraphrased from another plan.
- [x] `IssueQualificationReceipt.v1`'s absence is confirmed via direct search, not inferred.
- [x] The BugCheck-collision risk is named explicitly with two concrete resolution options, not glossed over.
- [x] This document does not itself close any `BDS-RMCP-FC-GIR-v0.1` gate item — it is the first step toward closing one.
