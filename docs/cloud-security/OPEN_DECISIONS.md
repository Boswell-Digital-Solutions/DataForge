# CSSA Open Decisions — Status & Phase 0 Resolutions

Tracks the seven open decisions in `CSSA_AUTHORITY_PLAN.md` §35. Per the plan, these must be resolved
before their corresponding implementation phase but **do not block Phase 0 acceptance**. Phase 0
requires only that **signing authority is identified** (OPEN-1); the rest carry a recommended
resolution and an assigned owner so the blocking phase can ratify quickly.

Status legend: **Resolved** (ratified, firm) · **Identified** (named, ratify before phase) ·
**Proposed** (recommendation recorded, owner to ratify) · **Deferred** (intentionally pushed to a
later schema version).

| # | Decision | Status | Must resolve before |
| --- | --- | --- | --- |
| OPEN-1 | Signing authority | **Identified** | Phase 2 (dev key), Phase 8 (production) |
| OPEN-2 | Durable outbox implementation | **Proposed** | Phase 3 |
| OPEN-3 | Quota authority | **Proposed** | Phase 6 |
| OPEN-4 | Local quarantine implementation | **Proposed** | Phase 6 |
| OPEN-5 | Response-classification timing | **Proposed** | Phase 5 |
| OPEN-6 | Regional / residency rules | **Deferred → v2** | Phase 10 (revisit) |
| OPEN-7 | Key rotation | **Proposed** | Phase 2 |

---

## OPEN-1 — Signing authority *(Identified — required for Phase 0 gate)*

**Question:** Does ForgeCommand sign initial production policy bundles, or does a separate ecosystem
signing service own the root?

**Identification (Phase 0):**

- **Development / Phases 2–7:** a repository-trusted development signing key (ed25519), checked into
  the ForgeAgents trust store and used only in SHADOW/CANARY non-production contexts (plan §11.2).
- **Production / Phase 8 (ACTIVE):** **ForgeCommand** is identified as the production policy-bundle
  signing authority, consistent with its ownership of entitlement, approval resolution, and Stripe
  plan state (plan §11.3, §30). A dedicated ecosystem signing service remains an allowed future
  substitution **provided** it is named and its root key published before any ACTIVE promotion.

**Rationale:** ForgeCommand already owns the entitlement/approval truth that the policy bundle binds.
Co-locating production signing avoids a second root of trust before one is operationally justified.
The development key never validates in production builds (production OFF/unsigned is prohibited — plan
§10.2, accepted decision §34.10/§34.12).

**Owner to ratify:** ForgeCommand maintainers (production root) + ForgeAgents maintainers (dev key).

---

## OPEN-2 — Durable outbox implementation *(Proposed)*

**Question:** DataForge intent stream, durable message broker, or encrypted local spool?

**Proposed resolution:** Primary = **DataForge append-only intent stream**
(`CLOUD_SECURITY_OUTBOX_MODE=dataforge`, aligned with `CLOUD_SECURITY_RECEIPT_TARGET=dataforge`).
Fallback for AuthorForge/edge origins where DataForge is unreachable = **narrowly scoped encrypted
local spool** with retention and recovery rules (plan §22.4). An in-memory retry queue is explicitly
insufficient.

**Rationale:** DataForge is the durable-truth boundary (`CLAUDE.md` critical rule 1). Reusing the
append-only ledger keeps audit truth in one place and avoids standing up a broker before scale demands
it. The encrypted-spool fallback preserves write-before-execute at origins partitioned from DataForge.

**Owner to ratify:** DataForge maintainers. **Resolve before:** Phase 3.

---

## OPEN-3 — Quota authority *(Proposed)*

**Question:** Does atomic reservation live in DataForge or a dedicated entitlement/quota service?

**Proposed resolution:** Atomic quota reservation persistence lives in **DataForge** for Phases 6–9
(plan §13, §30). The reserve→commit→release lifecycle is backed by a DataForge table with
per-quota-bucket atomicity (e.g. row-level locking / conditional update), not observational counters.
A future dedicated quota service (Phase 10, ForgeCommand entitlement API v1 + Stripe) may take over
ownership **behind the same `quota_reservation.v1` contract** without changing CSSA call sites.

**Rationale:** Keeps durable quota state in the durable-truth boundary and lets reservation, receipt,
and outcome records share one transactional store, which is what atomicity (invariant §10) needs.

**Owner to ratify:** DataForge + ForgeCommand maintainers. **Resolve before:** Phase 6.

---

## OPEN-4 — Local quarantine implementation *(Proposed)*

**Question:** Shared library, AuthorForge-owned vault, or app-specific encrypted stores behind one
contract?

**Proposed resolution:** **App-specific encrypted stores behind one shared quarantine-reference
contract** (plan §24.3), with raw content held **origin-local by default**. DataForge and
DataForge-Local store quarantine **references and metadata only**, never raw quarantined content by
default (plan §24.1–24.2). AuthorForge owns the customer-local vault for manuscripts/source; each app
implements storage but conforms to the single reference/release contract.

**Rationale:** Honors invariant §9 (raw content stays at origin) and `CLAUDE.md` security posture
without forcing a single central vault that would itself become a high-value raw-content target.

**Owner to ratify:** AuthorForge + ForgeCommand maintainers. **Resolve before:** Phase 6.

---

## OPEN-5 — Response-classification timing *(Proposed)*

**Question:** Synchronous before delivery for all classes, or async for R0/R1 non-chained responses?

**Proposed resolution:** **Synchronous, before delivery** for any response that is R2+ in its request
classification, is chained into another tool, or crosses a trust boundary (plan §14.5). **Async
permitted** only for R0/R1 responses that are non-chained and not crossing a boundary. Classifier
failure always produces a fail-closed recommendation (plan §9, Phase 5 gate).

**Rationale:** Guarantees no secret/PII reaches a log, store, or downstream tool unclassified, while
keeping the metadata-latency budget achievable for the common low-risk path.

**Owner to ratify:** ForgeAgents maintainers. **Resolve before:** Phase 5.

---

## OPEN-6 — Regional / residency rules *(Deferred → v2)*

**Question:** Does provider eligibility need jurisdiction and data-residency fields in v1 or v2?

**Proposed resolution:** **Deferred to contract v2.** v1 contracts (Phase 1) do **not** add residency
fields, but the provider-firewall law (§25) already states a provider is ineligible when residency
forbids it. Residency enters as a v2 field set when a customer/plan requires jurisdiction pinning,
surfaced through the Phase 10 ForgeCommand entitlement API.

**Rationale:** Avoids speculative schema surface before a concrete residency requirement exists;
breaking additions are a clean v2 per plan §16.

**Owner to ratify:** ForgeCommand + ForgeAgents maintainers. **Revisit at:** Phase 10.

---

## OPEN-7 — Key rotation *(Proposed)*

**Question:** Policy-bundle key rotation, overlap, revocation, and emergency rollover process?

**Proposed resolution:** Policy bundles carry `key_id` (plan §11.1). Validators trust a **set** of
active public keys, enabling **overlapping rotation**: a new key is added to the trust set before any
bundle signs with it, and the old key is retired only after all bundles signed with it have expired
(bounded by `expires_at`). **Revocation** removes a `key_id` from the trust set immediately and
invalidates bundles signed by it (fail-closed, `POLICY_SIGNATURE_INVALID`). **Emergency rollover**
combines revocation with the kill switch (`CLOUD_SECURITY_KILL_SWITCH=block_all`) until a freshly
signed bundle propagates. Anti-rollback version prevents replay of a superseded bundle.

**Rationale:** Overlapping multi-key validation is the standard way to rotate without downtime; tying
revocation to fail-closed + kill switch keeps it consistent with §9.

**Owner to ratify:** ForgeCommand (key custodian) + ForgeAgents maintainers. **Resolve before:**
Phase 2 (loader must support a key set, not a single key).

---

## Ratification log

Append ratifications as `OPEN-N — ratified by <group> on <date>, commit <sha>`:

- _(none yet — Phase 0 records identification/proposals; ratifications land per phase)_
