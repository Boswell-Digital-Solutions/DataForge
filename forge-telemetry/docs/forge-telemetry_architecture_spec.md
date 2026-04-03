# forge-telemetry Architecture Spec

**Document version:** 1.0 (2026-04-03) — Nested repo protocol adoption

## 1. Purpose

This spec records the current observable architecture of the `forge-telemetry` library repo.
It is intentionally scoped to implemented package surfaces, not aspirational service behavior.

## 2. Current Implementation State

| Surface | Current truth |
| --- | --- |
| Canonical technical reference | `doc/system/` plus generated root `SYSTEM.md` |
| Repo-local instructions | `CLAUDE.md` |
| Current maturity | Small shared library with completed documentation stack and limited/no automated tests yet |

## 3. Module Map

| Module | Surface | Current role |
| --- | --- | --- |
| Documentation Stack | `doc/system/`, `SYSTEM.md`, `scripts/context-bundle.sh` | Canonical repo context and generated reference |
| Package Surface | `forge_telemetry/`, `src/forge_telemetry/` | Public client/model exports and alternate layout mirror |
| Packaging | `setup.py`, `requirements.txt`, `forge_telemetry.egg-info/` | Install metadata and dependency declaration |
| Verification | `tests/` | Reserved verification surface; currently empty and should grow with behavior changes |

## 4. Architectural Boundary

- this repo is a library boundary, not a resident service
- it emits into the shared `events` table but does not own that table or its migrations
- when this spec and `SYSTEM.md` diverge, `SYSTEM.md` wins as the implemented reality reference
