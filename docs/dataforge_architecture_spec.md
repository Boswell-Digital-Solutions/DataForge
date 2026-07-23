# DataForge Architecture Spec

**Document version:** 1.2 (2026-07-23) — FT-02 telemetry ingress parity

## 1. Purpose

This architecture spec records the current repo truth for DataForge as a live resident service.
It is intentionally narrower than historical phase summaries and only documents surfaces that
can be observed in the working tree.

## 2. Current Implementation State

| Surface | Current truth |
| --- | --- |
| Canonical technical reference | `doc/system/` plus generated root `SYSTEM.md` (with mirrored `doc/SYSTEM.md` and legacy `doc/dfSYSTEM.md`) |
| Repo-local instructions | `CLAUDE.md` |
| Current maturity | Resident FastAPI service with mounted product, governance, operator-control, and authenticated generic telemetry surfaces |
| Route posture | `46` mounted router objects in `app/main.py`; additional routers remain source-present only until mounted |
| Schema posture | Modular `app/models/` layout including hash-pinned FT-02 telemetry resource-bound consumption |

## 3. Module Map

| Module | Surface | Current role |
| --- | --- | --- |
| Documentation Stack | `doc/system/`, `SYSTEM.md`, `scripts/context-bundle.sh`, `README.md` | Canonical repo context, generated reference, operator entrypoint |
| Resident Service Runtime | `app/`, `templates/`, `static/` | FastAPI app, mounted routes, middleware, HTML operator surfaces |
| Domain Persistence | `app/models/`, `alembic/`, `alembic.ini` | Durable truth for documents, runs, policy envelopes, promotion receipts, Sentinel state, press automation, and more |
| Integration and Governance Surfaces | `app/api/`, `app/auth/`, `app/utils/` | Product APIs, authenticated telemetry ingress, key/token control, search, cache governance, auth, resilience, and policy/runtime evidence |
| Verification | `tests/`, `pytest.ini` | API, integration, unit, governance, security, and opt-in load testing |
| Supporting Doctrine | `docs/`, `ops/`, `diligence/` | Architecture, runbooks, references, and compliance/supporting material |
| Nested Repo Boundary | `forge-telemetry/` | Separate git repo with its own docs stack; do not treat as part of the DataForge runtime tree |

## 4. Architectural Boundary

- DataForge is the durable-truth and retrieval boundary, not the ecosystem orchestrator.
- Redis remains derived state only; authoritative decisions fall back to Postgres-backed truth.
- Source-present routers are not contractually live unless mounted in `app/main.py`.
- When this spec and generated `SYSTEM.md` diverge, generated `SYSTEM.md` wins.
