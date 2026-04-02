# Runtime Promotion Execution Handoff — Carry-Forward Context

## Current state

The runtime-promotion execution-handoff slice is materially green and stronger again.

Latest targeted results:

- `tests/test_runtime_promotion_execution_worker.py` → **16 passed**
- `tests/test_runtime_promotion_candidates.py` → **4 passed**
- each targeted run still shows **1 warning**

Current remaining warning posture:

- passlib `crypt` deprecation warning remains external to the runtime-promotion slice

---

## What is now proven

### Claim and control seam

Proven:

- duplicate-safe claim behavior
- queued request claimability
- terminal-state non-claimability
- single-winner claim behavior across separate sessions
- repeated multi-session contention hardening keeps one winner per round
- higher-session bounded contention pressure still keeps one winner and one accepted-status writeback

### Worker lifecycle seam

Proven:

- accepted → running → completed path
- invalid bounded-parameter fail-closed path
- unsupported subsystem fail-closed path
- unsupported requested-action fail-closed path
- unacceptable authorization-class fail-closed path
- explicit timeout path
- explicit dead-letter path

### Verification closeout seam

Proven:

- execution completion remains separate from verification truth
- verification writeback is durable
- candidate detail readback shows execution and verification separately
- completion is not collapsed into verification success
- the integrated worker-to-verification closeout path is directly proven end to end
- verification evidence is explicitly grounded in the richer maintenance payload
- verification summary explanation is now more operator-legible and explicitly grounded in that same bounded maintenance evidence

### Real low-risk side-effect seam

Proven:

- the first bounded lane performs one real low-risk durable side effect
- the side effect is a bounded writeback onto the execution request’s `bounded_parameters_json`
- the side effect is operator-legible and low blast radius
- the side effect is visible both in direct DB inspection and in candidate-detail readback
- the side effect has now been enriched into a richer bounded maintenance evidence payload

---

## What changed in this pass

### 1. Verification summary refinement is now implemented and proven

Verification no longer stops at evidence refs plus a generic summary only.

The verification path now produces more operator-legible summary language that can explicitly state the bounded basis used for verification.

That basis can now directly reference:

- `worker_execution_result` presence
- `maintenance_action_class`
- `target_capability`

This keeps verification separate from execution while making the verification explanation clearer and more grounded.

### 2. Higher-session race-style contention pressure remains proven

The worker suite continues to prove a stronger contention pass where:

- higher session counts contend for the same eligible request
- only one claimant still wins
- only one accepted-state status row is written
- the claim seam does not amplify accepted-status writeback under heavier bounded pressure

### 3. Verification evidence grounding remains proven

Verification continues to write evidence refs that explicitly confirm:

- `worker_execution_result` is present
- `maintenance_action_class` matches the expected maintenance action
- `target_capability` matches the expected narrow target

### 4. Readback remains clean without router widening

No router widening was required for the stronger contention pass, verification-evidence grounding pass, or verification-summary refinement pass.

Reason:

- execution request contracts already surface `bounded_parameters`
- candidate-detail execution handoff already serializes the execution request contract
- verification artifacts were already wired into candidate-detail readback separately from execution summary

That means stronger claim/control proof, richer maintenance evidence, more explicit verification grounding, and clearer verification explanation all remain visible through the existing governed readback surface.

---

## Current first-lane posture

The first bounded lane remains:

- one lane only: `local_runtime_action`
- one bounded action family only
- fail-closed before side effects
- durable lifecycle writeback
- execution kept separate from verification
- one real low-risk downstream effect proven
- richer bounded maintenance evidence proven
- integrated worker-to-verification closeout proven
- stronger higher-session contention proof proven
- verification evidence grounded in the maintenance payload proven
- verification summary explanation grounded in the maintenance payload proven

This is still intentionally narrow.
It is not a broad remediation engine.

---

## Files materially involved in the current baseline

### Worker logic
- `app/runtime_promotion/execution_handoff/worker.py`

### Execution request / verification services
- `app/runtime_promotion/execution_handoff/service.py`

### Execution status helpers
- `app/runtime_promotion/execution_handoff/status_service.py`

### Candidate readback route
- `app/api/runtime_promotion_candidate_router.py`

### Worker proving suite
- `tests/test_runtime_promotion_execution_worker.py`

### Candidate proving suite
- `tests/test_runtime_promotion_candidates.py`

---

## Recommended next bounded move

The best next bounded move is:

**decide whether to widen beyond the first action family at all**

Meaning:

- keep one lane only unless there is a concrete second action worth proving
- do not widen for abstract completeness
- either:
  - add one second bounded action shape inside the same lane, or
  - declare the first-lane baseline stable and stop widening for now

Possible bounded follow-on directions:

1. treat the current first-lane baseline as stable and shift emphasis to documentation and control-surface discipline
2. add one second bounded action shape only if there is a concrete real operator need
3. avoid widening just to satisfy generic completeness instincts

---

## Bottom line

This slice is no longer just persistence-only handoff theory.

It now has repo-proven worker coverage for:

- claim once
- claim from queued
- refuse terminal-state reclaim
- allow only one winner across separate sessions
- keep one winner across repeated bounded contention rounds
- keep one winner and one accepted-state writeback under higher-session bounded contention pressure
- run once
- fail closed on invalid input
- fail closed on unsupported subsystem/action
- fail closed on unacceptable authorization posture
- time out explicitly
- dead-letter durably
- write back durably
- perform one real low-risk downstream side effect
- enrich that side effect into a richer bounded maintenance evidence payload
- surface that side effect through candidate-detail readback
- complete execution and then verify separately
- prove the integrated worker-to-verification closeout path end to end
- ground verification evidence explicitly in the richer maintenance payload
- ground verification summary explanation explicitly in the richer maintenance payload

That is the current bounded execution-lane baseline.