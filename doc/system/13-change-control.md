# §13 — Change Control

**Truth class:** canonical doctrine

This chapter defines how changes to DataForge are classified, evidenced,
verified, and rolled back. It is practical and enforceable: every change class
names the evidence and verification commands that must accompany it. DataForge is
an internal Forge ecosystem service; nothing here authorizes public-release or
production-certification claims.

## Change Classes

| Class | Scope | Example |
|-------|-------|---------|
| C0 | Documentation only | Editing `doc/system/` chapters, rebuilding `doc/DTFSYSTEM.md` |
| C1 | Schema / migration | New/changed ORM models, Alembic migrations, pgvector index |
| C2 | API surface | Mounting/altering a router, request/response contract changes |
| C3 | Retrieval | Embedding model/dimension, chunking, hybrid-search/RRF tuning |
| C4 | Write-boundary / access control | Token scopes, key rotation, run immutability, audit log |
| C5 | Runtime governance | Promotion receipts, policy envelopes, rate limits, evidence tables |
| C6 | Configuration / security | `config` env contract, encryption, secrets, readiness signals |

## Required Evidence Per Change Class

- **C0** — rebuilt artifact (`bash doc/system/BUILD.sh` → `BUILD_OK`), edited
  source chapter (never a hand-edit to `doc/DTFSYSTEM.md`).
- **C1** — the Alembic migration file + `alembic upgrade head`/`downgrade`
  applied cleanly; the migration count in §1/§9 re-measured.
- **C2** — the router mounted in `app/main.py` (or explicitly noted as
  source-present-not-mounted), with contract tests covering the new surface.
- **C3** — evidence the embedding dimension stays consistent with stored vectors
  (a dimension change is a migration, not a config tweak) and search quality is
  not silently degraded.
- **C4** — proof the access-control matrix still holds (ForgeCommand/BugCheck/
  XAI/VibeForge write scopes), the AuthorForge analytics-only/local-content boundary,
  run-immutability (409 after FINALIZED), and the
  audit log remains append-only + HMAC-signed.
- **C5** — the governance-evidence table/flow with operator-review surfacing.
- **C6** — the env/setting reflected in §14 (Configuration), with secrets sourced
  from the vault/secret-sync path and readiness driven by DB/pgvector (not Redis).

## Required Verification Commands

```bash
PYTHONPATH=. ./.venv/bin/pytest -q            # full suite
pytest --cov=app tests/                       # coverage
alembic upgrade head                          # schema changes (C1)
ruff check app/ && mypy app/                  # lint + types
bash doc/system/BUILD.sh                       # doc changes (C0) -> BUILD_OK designation=DTF
curl -s localhost:8001/ready                   # fail-closed readiness (DB + pgvector)
```

## Source-of-Truth / Fail-Closed Rules

DataForge stays the canonical durable record for its approved domains (§11): a change must not
introduce a path where DataForge-owned state is considered complete without being persisted
here. This rule never authorizes AuthorForge content ingestion; that content must remain local
and any cloud attempt must fail closed. Readiness stays DB/pgvector-driven; Redis remains derived state.
The mounted surface is the live contract — adding a router to source without
mounting it does not change the contract (note it as source-present-not-mounted).

## Documentation Change Rules (C0)

`doc/system/` source modules are the only editing surface. The compiled
`doc/DTFSYSTEM.md` is regenerated, never hand-edited (§12). Snapshot facts
(router/migration/test counts) are re-measured and re-dated, not asserted as
guarantees.

## Release / Readiness Claim Rules

No change may introduce public-release, public-SaaS, or production-certification
language, or present a coverage percentage as a guarantee, unless a governed
release slice proves that specific claim.
