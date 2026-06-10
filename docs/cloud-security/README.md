# Cloud Service Security Authority (CSSA) — DataForge docs

This directory holds the DataForge-resident copy of the **ForgeAgents Cloud Service Security
Authority** plan and its phase artifacts. CSSA governs every cloud-connected action in the Forge
ecosystem so that it is *attributable, classified, entitled, policy-checked, quota-reserved,
authorized, executed through a governed egress path, and reconstructable from immutable records.*

## Reading order

1. **[`CSSA_AUTHORITY_PLAN.md`](./CSSA_AUTHORITY_PLAN.md)** — the canonical authority model:
   invariants, identity/entitlement/quota/data-boundary law, contract family, decision and record
   schemas, the 11-phase rollout plan, and the verification matrix. Reference law for all phases.
2. **[`PHASE_0_ACCEPTANCE.md`](./PHASE_0_ACCEPTANCE.md)** — the Phase 0 (Authority lock) acceptance
   record: gate checklist, consistency review against DataForge critical rules and telemetry trust
   laws, the cross-repo ownership sign-off matrix, and the DataForge-side boundary acceptances.
3. **[`OPEN_DECISIONS.md`](./OPEN_DECISIONS.md)** — status, owners, and Phase 0 resolutions for the
   seven open decisions (plan §35), including the identified signing authority.

## Current phase

**Phase 0 — Authority lock.** This branch lands the authority model and acceptance artifacts only.
Per the Phase 0 "no advance" rule, **no contract schemas, Pydantic models, or `app/security/` code
land until acceptance is countersigned.** Phase 1 (Contract kernel) begins after the §5 ownership
matrix in `PHASE_0_ACCEPTANCE.md` is fully signed.

## DataForge's role in CSSA

Per plan §30, DataForge is the **durable append-only security ledger** and the home of **quota
reservation persistence**. DataForge stores CSSA records and quarantine *references/metadata* — never
raw quarantined customer content by default (plan §24). DataForge does not own entitlement, approval,
lifecycle, or rollout state; those belong to ForgeCommand.
