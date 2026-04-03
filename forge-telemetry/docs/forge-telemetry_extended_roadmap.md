# forge-telemetry Extended Roadmap

**Document version:** 1.0 (2026-04-03) — Nested repo protocol adoption

## Current Status

| Phase | Status | Outcome |
| --- | --- | --- |
| Documentation normalization | Complete | Root `SYSTEM.md`, `CLAUDE.md`, architecture spec, roadmap, and context loader are now present |
| Exact surface catalog | Complete for current repo size | Package files, env resolution, and fail-open behavior are documented |
| Verification hardening | Pending | Add package tests for DB resolution, fail-open behavior, and event-model validation |

## Phase 0 — Documentation Normalization

**Goal:** establish the full Forge documentation stack for this nested repo.

## Phase 1 — Library Verification

**Goal:** add focused tests for URL resolution, required-mode failures, and public export stability.

## Phase 2 — Contract Expansion

**Goal:** extend service vocabulary and event helpers only when upstream Forge services require it.
