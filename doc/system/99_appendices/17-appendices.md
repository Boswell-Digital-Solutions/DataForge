# §17 — Appendices

**Document version:** 1.0 (carry-forward)

Appendices, glossary, and cross-references.

## Revision history

| Version | Date | Change |
|---------|------|--------|
| 2.0 | 2026-06-19 | Migrated the compiled reference to the BDS canonical-compliance documentation structure. |
| 2.1 | 2026-07-23 | Documented the authority-pinned FT-02 65,536-byte complete canonical telemetry-event boundary and stable `event_size_exceeded` behavior. |
| 2.2 | 2026-07-23 | Pinned the admitted ForgeEvent.v1 expected-error profile and documented code-only, value-free canonical ingress validation. |
| 2.3 | 2026-07-23 | Replaced DataForge search's pre-v1 direct-database emitter with the privacy-bounded canonical async HTTP producer and finite shutdown contract. |

## Unmapped legacy chapters

The following legacy chapters were carried forward but could not be
deterministically mapped to a class-aware slot. Review and place them by
hand:

- `DataForge System Documentation`
- `§3 — Technology Stack`
- `§5 — Configuration & Environment Variables`
- `Database`
- `Security`
- `Server`
- `AI Providers`
- `Chunking`
- `Logging`
- `§6 — API Layer`
- `§7 — Backend Internals`
- `pgvector cosine similarity query`
- `PostgreSQL TSVECTOR + ts_rank`
- `§8 — Ecosystem Integration Contracts`
- `§9 — Error Handling, Lifecycle & Access Control`
- `Default fingerprint`
- `Category-specific fingerprints`
- `API Contract Drift:`
- `Dependency CVE:`
- `Flaky Test:`
- `§10 — Testing`
- `§11 — Handover, Critical Constraints & Migration Runbook`
- `1. Install any new dependencies`
- `2. Run migrations`
- `2a. Refresh the canonical model catalog when model identifiers or pricing change`
- `2b. Refresh governed policy whitelists after catalog changes`
- `3. Verify migrations applied cleanly`
- `4. Run tests to confirm nothing broke`
- `5. Start service`
- `Auto-generate migration from ORM model changes`
- `Review the generated file in alembic/versions/`
- `Verify the upgrade() and downgrade() functions are correct`
- `Apply`
- `Verify`
- `Roll back one step`
- `Roll back to a specific revision`
- `View migration history`
- `Create admin user interactively`
- `Or set environment variables for non-interactive:`
- `§13 — Proving-Slice Schema`
