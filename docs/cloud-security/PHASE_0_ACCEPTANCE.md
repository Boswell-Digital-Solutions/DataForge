# CSSA Phase 0 — Authority Lock: Acceptance Record

**Phase:** 0 — Authority lock
**Date opened:** 2026-06-09
**Date recorded in DataForge:** 2026-06-10
**Branch:** `claude/dayaforge-cssa-phase-0-mhqcgg`
**Canonical plan:** [`CSSA_AUTHORITY_PLAN.md`](./CSSA_AUTHORITY_PLAN.md)

> **Phase 0 objective:** Accept the CSSA authority model and resolve (or assign owners to) all
> remaining open decisions. **No contract schemas, Pydantic models, or `app/security/` code land in
> this phase** — that is gated behind acceptance and begins in Phase 1 (Contract kernel).

This record is the DataForge-resident acceptance artifact. It does not grant any runtime authority;
per §3 of the plan, authority comes only from contracts, validators, authenticated policy artifacts,
immutable records, trusted runtime identity, quota reservations, approval records, and governed
egress enforcement.

---

## 1. Phase 0 gate checklist

| # | Gate item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | No contradictions with ForgeAgents / DataForge critical rules | ✅ Accepted | §3 below |
| 2 | No contradictions with telemetry trust laws | ✅ Accepted | §4 below |
| 3 | Ownership accepted by ForgeCommand, NeuroForge, AuthorForge, DataForge maintainers | ⏳ Pending sign-off | §5 sign-off matrix |
| 4 | Immutable audit lifecycle accepted | ✅ Accepted | §6 below |
| 5 | Quota reservation ownership accepted | ✅ Accepted | §6 below; OPEN-3 |
| 6 | Quarantine boundary accepted | ✅ Accepted | §6 below; OPEN-4 |
| 7 | Signing authority identified | ✅ Identified | OPEN-1 in `OPEN_DECISIONS.md` |
| 8 | No advance: no contract schemas land before acceptance | ✅ Held | This branch adds docs only |

Legend: ✅ recorded/accepted in-repo · ⏳ awaiting an external maintainer signature that this repo
cannot self-certify.

The only item this DataForge branch cannot unilaterally close is **cross-repo ownership sign-off**
(item 3), which requires the four named maintainer groups to countersign. The matrix in §5 is the
artifact they sign against. Everything else required of the DataForge side is recorded here.

---

## 2. What this branch delivers

- `docs/cloud-security/CSSA_AUTHORITY_PLAN.md` — canonical, repository-resident authority model.
- `docs/cloud-security/PHASE_0_ACCEPTANCE.md` — this acceptance record and gate checklist.
- `docs/cloud-security/OPEN_DECISIONS.md` — tracked status, owners, and Phase 0 resolutions for the
  seven open decisions in plan §35.
- `docs/cloud-security/README.md` — index and reading order.
- `CHANGELOG.md` entry recording Phase 0 acceptance.

It deliberately delivers **no** schemas under `schemas/cloud_security/`, **no** `app/security/`
modules, and **no** API router — those are Phase 1+ and are blocked by the "no advance" gate above.

---

## 3. Consistency with DataForge critical rules

The plan was reviewed against `CLAUDE.md` → *CRITICAL RULES (NON-NEGOTIABLE)*. No contradictions found.

| DataForge critical rule | CSSA plan position | Verdict |
| --- | --- | --- |
| DataForge owns all durable state | Plan §30 assigns DataForge the "durable append-only security ledger" and "quota reservation persistence"; CSSA only reads/writes through DataForge. | Consistent |
| BugCheck writes findings only; never lifecycle | Out of scope; CSSA adds no BugCheck write path. CSSA writes only its own decision/authorization/outcome records. | No conflict |
| VibeForge never writes findings | Out of scope; unaffected. | No conflict |
| Audit log is immutable, append-only, HMAC-signed | Plan §22 mandates immutable, append-only, hash-covered records with no back-fill. CSSA records extend, never relax, this rule. | Consistent / reinforcing |
| After FINALIZED, reject new findings with 409 | CSSA does not write lifecycle/finalization; §3 of the plan explicitly excludes lifecycle-state writing. | No conflict |

**Authority boundary confirmation:** CSSA never writes lifecycle, entitlement, approval-resolution,
or rollout state (plan §3, §11.3, §23, §27.2). ForgeCommand remains the lifecycle/entitlement/approval
authority; DataForge remains the durable-truth boundary. CSSA is a consumer and a producer of its own
immutable records only.

---

## 4. Consistency with telemetry trust laws

Reviewed against the nested `forge-telemetry/` trust boundary and the immutable-audit posture in
`CLAUDE.md` → *Security Notes*.

- CSSA records are **evidence**, not assertions: every governed attempt yields a hash-covered record
  (plan §4.4–4.6, §22). This matches the telemetry principle that trust derives from signed, immutable
  evidence rather than prompt/UI claims.
- CSSA emits incidents as references, not raw payloads (plan §9 Phase 9 gate, §27). This preserves the
  telemetry rule that evidence carries references, not sensitive content.
- The watchdog is powerless by construction (plan §27.2): it cannot inject decisions, matching the
  telemetry separation between observation and enforcement.

No contradiction with telemetry trust laws found.

---

## 5. Ownership sign-off matrix

Each maintainer group countersigns acceptance of **its** responsibilities in plan §30 and the
invariants in §4. Sign-off is recorded by appending name, date, and commit SHA below.

| Maintainer group | Accepts (plan reference) | Status | Signed by / date |
| --- | --- | --- | --- |
| ForgeCommand | entitlement ownership, Stripe plan state, approval resolution, incident lifecycle, operator UI; consumes but does not rewrite authorization truth (§4.14, §11.3, §23, §30) | ⏳ Pending | _________ |
| NeuroForge | routing optimization within the CSSA-bounded candidate set; cannot select a provider forbidden by data class/entitlement/residency/tier (§25, §30) | ⏳ Pending | _________ |
| AuthorForge | advisory evaluation + governed execution integration; customer-local artifact ownership and origin-local quarantine (§24, §30) | ⏳ Pending | _________ |
| DataForge | durable append-only security ledger + quota reservation persistence; storage availability and retention (§13, §22, §30) | ✅ Recorded in-repo | This branch / Phase 0 |

> DataForge's acceptance is recorded by landing this document on the designated branch. The remaining
> three groups sign in their own repositories or by countersigning this matrix; until then item 3 of
> the gate stays ⏳ and the plan does not advance to Phase 1 ACTIVE work.

---

## 6. Boundary acceptances (DataForge side)

**Immutable audit lifecycle (gate item 4):** Accepted. CSSA decision, authorization, and outcome
records are immutable and append-only with no back-fill of hash-covered fields (plan §22.1). This is a
strict superset of the existing DataForge audit-log rule and introduces no mutation path.

**Quota reservation ownership (gate item 5):** Accepted with owner assigned. Atomic quota reservation
persistence lives in **DataForge** (plan §13, §30; `CLOUD_SECURITY_RECEIPT_TARGET=dataforge`). See
OPEN-3 in `OPEN_DECISIONS.md` for the reserve→commit→release lifecycle persistence contract that
Phase 6 will implement. Reservations are atomic per quota bucket; observational counters alone are
insufficient.

**Quarantine boundary (gate item 6):** Accepted. Raw customer content is quarantined **origin-local by
default** (plan §24.1). DataForge-Local must not receive raw customer manuscripts, source code,
documents, or secrets except under the explicit conditions in §24.2. DataForge stores quarantine
*references and metadata only*, never raw quarantined content by default. See OPEN-4.

---

## 7. Exit criteria → Phase 1

Phase 1 (Contract kernel) may begin once the §5 matrix is fully countersigned. Phase 1 lands, under
`schemas/cloud_security/v1/` and `app/security/contracts.py`:

- the seven JSON Schema 2020-12 contracts (decision, authorization, outcome, incident, quota
  reservation, policy bundle, classification attestation),
- Pydantic v2 models, reason-code enums, valid/invalid fixtures, and RFC 8785 hashing tests.

Phase 1 gate: schemas validate and reject fixtures correctly; no mutable/back-filled hash-covered
fields; contract cardinality tests pass; hash stability proven; mypy and ruff clean.

Until then, the "no advance" rule holds: **no contract schemas land.**
