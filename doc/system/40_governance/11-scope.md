# §11 — Scope

**Truth class:** canonical doctrine

This `doc/system/` tree is the modular source of the **DataForge compiled system
reference**, assembled into the designation-bound artifact `doc/DTFSYSTEM.md`
(designation `DTF`) via `bash doc/system/BUILD.sh`. This chapter defines
DataForge's service authority and the boundaries that separate it from the rest
of the Forge ecosystem. DataForge is an internal Forge ecosystem service. It is
not a public product, not a SaaS offering, and nothing here asserts
public-release or production-certification status.

## DataForge Service Authority

DataForge is the **durable-truth boundary** for the Forge ecosystem — the
resident FastAPI persistence, retrieval, and governance-evidence service. Its
authority is durable and ecosystem-wide: state written here is the *canonical
record*, not a convenience mirror. Every major Forge runtime persists its
authoritative records into DataForge, and if a service cannot persist required
durable state here, the operation is **not complete** (fail-closed by design).

## What DataForge Owns

- **Durable persistence** — PostgreSQL is the authority boundary for documents,
  runs, findings, planning state, authoring assets, pricing/catalog data, policy
  ledgers, press-automation records, and private-source profiles.
- **Hybrid retrieval** — chunked documents with pgvector embeddings + full-text
  indexes, served as semantic, keyword, and RRF-fused search.
- **Scoped write enforcement** — run-scoped write flows, service-key validation,
  admin-key rotation, and admin-token-protected control surfaces (the live
  *mounted* surface; a richer secure-auth stack exists in source but is not part
  of the live contract until mounted).
- **Runtime governance evidence** — policy envelopes, policy ledgers, reward
  records, runtime-promotion receipts, candidate approvals/rejections, rate-limit
  state, and execution evidence for operator review.
- **Append-only audit truth** — the immutable, HMAC-signed audit log.

## What DataForge Does Not Own

- **Orchestration / control.** ForgeCommand is the ecosystem operator/control
  plane; DataForge does not schedule, transition lifecycles on its own behalf, or
  grant governed overrides.
- **Autonomous repair.** Sentinel records are persisted here, but DataForge does
  not itself perform remediation.
- **Cache authority.** Redis accelerates reads/rate-limits and holds derived
  state only — it never owns truth; pgvector + Postgres readiness drive the
  authoritative ready signal.
- **The live OAuth2/TOTP gateway** on the default mounted surface (those secure
  modules are source-only until explicitly wired).
- **The `forge-telemetry/` codebase.** That nested repo is versioned and
  documented separately and is out of this documentation boundary.

## Write-Boundary / Access-Control Authority

DataForge enforces *who may write what* at the API boundary: ForgeCommand writes
run records, lifecycle transitions, and finalization (admin token); BugCheck
writes findings/progress/telemetry only (run_token); XAI/MAID write enrichment
only (run_token); VibeForge writes user decisions only (user_token). After a run
is FINALIZED, new findings are rejected with 409 (run immutability). These
boundaries are invariants, not suggestions.

## Release / Readiness Language Restrictions

This documentation describes an internal service under governed development. It
must be described as a verification-current internal service, not as externally
release-certified, and must not claim public-release/SaaS readiness or present
coverage percentages as guarantees unless a later governed slice proves the
specific claim.

## Documentation truth classes

Every statement in this documentation system belongs to one of two classes:

- **Canonical facts** define DataForge's source-of-truth contract, persistence
  and retrieval authority, write-boundary/access-control invariants, fail-closed
  readiness posture, and ecosystem contracts. They change only through deliberate
  change control (§13).
- **Snapshot facts** are audit-derived counts — mounted routers, migrations,
  Python/test files, collected tests — labelled with a measurement date. They may
  drift between rebuilds and are corrected by re-measurement, not change control.

Ownership, designation doctrine, and the authority hierarchy that govern this
tree are defined in §12.
