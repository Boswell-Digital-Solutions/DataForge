# DataForge — Claude Code Context

Durable-truth boundary for the Forge ecosystem. FastAPI, port 8001, entry `app/main.py`.

Full reference: `doc/DTFSYSTEM.md` (designation DTF), built from `doc/system/` via
`bash doc/system/BUILD.sh`. Config surface: `.env.example` and `app/config.py`.

---

## Authority

DataForge owns durable state for approved domains and enforces who may write what.

| Caller | May write | Credential |
|---|---|---|
| ForgeCommand | run records, lifecycle transitions, finalization | admin token |
| BugCheck | findings, progress events, check telemetry | `run_token` (30–60 min) |
| XAI / MAID | enrichment artifacts only | `run_token` |
| VibeForge | user decisions only | `user_token` |

**AuthorForge is the standing exception:** its embedded database exclusively owns projects and
user content. DataForge accepts only strict-minimized `AuthorForgeAnalyticsEnvelope.v1` telemetry
— never content, identity, paths, raw logs, prompts/responses, attachments, or embeddings.
The content routers are **retired**; do not remount them.

Enforced by:

- `tests/test_unit/test_authorforge_boundary_audit.py` — 410 tombstone on content paths
- `tests/test_unit/test_authorforge_analytics.py` — envelope minimization
- `tests/test_security/test_rls_public_tables.py` — row-level security on public tables
- `tests/test_cloud_security_ledger.py` — ledger integrity

Audit log is append-only with HMAC-SHA256 signatures — never modify a written row. After a run is
FINALIZED, new findings are rejected with 409.

---

## Verification

```bash
bash scripts/preflight.sh     # canonical gate: deps → single alembic head → pytest
```

`make test`, `make lint`, `make format`, and `make health` wrap the same tools for narrower loops.
Postgres-backed proofs live in `scripts/prove_*.sh` (ForgeEvent.v1 storage, telemetry CP2–CP6).

---

## Non-obvious

- **The migration chain refuses to downgrade past `20260724_01`** — it is evidence-preserving by
  design. Rolling back needs a new retirement migration, not a `downgrade()`.
- Preflight fails on multiple Alembic heads. Merge heads before you ship.
- Many routers exist in `app/api/` but are deliberately **not mounted** in `app/main.py`
  (`auth_secure_router`, `projects_router`, `dlq_router`, `replication_router`, and others).
  Source presence is not activation — check `app/main.py` before assuming an endpoint is live.
- Embedding dimensions are pinned at 1536; embeddings across providers are not interchangeable.

```bash
./scripts/context-bundle.sh --list          # focused context presets: core, api, schema, testing
```
