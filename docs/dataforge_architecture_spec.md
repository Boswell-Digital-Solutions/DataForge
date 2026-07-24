# DataForge Architecture Spec

**Document version:** 1.3 (2026-07-24) — CP2 bounded-recovery pilot

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

### CP2 producer recovery pilot

DataForge's search producer retains the authenticated canonical HTTP transport
as its only downstream sink. When `DATAFORGE_TELEMETRY_SPOOL_PATH` is explicitly
set, the producer first commits validated canonical bytes to the SDK-owned
private SQLite spool and one application-owned worker drains bounded batches.
The pilot has no listener, daemon, Redis queue, legacy API, direct database
producer, or compatibility write.

The spool is capped at 512 entries and 32 MiB. Drain passes claim at most four
events, use at most five delivery attempts with 1–30 second backoff, open a
15-second circuit after three consecutive downstream failures, and pause
acknowledgement-loss outcomes as `indeterminate`. Such rows require explicit
operator duplicate-risk review before retry. Unsetting the spool path restores
the CP1b direct canonical HTTP mode; it does not restore any pre-v1 path.

The sink side uses `app/telemetry_database.py`, never the business session
dependency. Enabled writes require a distinct PostgreSQL login that inherits
only `dataforge_telemetry_ingest`. Runtime preflight rejects the business
username, privileged/`BYPASSRLS` logins, missing membership, and the wrong
application name. Each process receives a two-connection pool with zero
overflow plus finite checkout, connect, statement, lock, and transaction
timeouts. A 20 events/second, 40-event burst budget rejects excess intake before
telemetry checks out a connection.

## 4. Architectural Boundary

- DataForge is the durable-truth and retrieval boundary, not the ecosystem orchestrator.
- Redis remains derived state only; authoritative decisions fall back to Postgres-backed truth.
- Source-present routers are not contractually live unless mounted in `app/main.py`.
- When this spec and generated `SYSTEM.md` diverge, generated `SYSTEM.md` wins.
