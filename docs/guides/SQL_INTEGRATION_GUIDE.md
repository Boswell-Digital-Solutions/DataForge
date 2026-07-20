# AuthorForge / DataForge Boundary Guide

> Supersedes the historical AuthorForge SQL-integration design. Do not configure AuthorForge
> to use DataForge PostgreSQL, call `/api/projects`, or sync an embedded database to DataForge.

## Authority

AuthorForge's embedded database is the exclusive source of truth for AuthorForge projects and
all user-authored or user-derived content. This includes manuscripts, chapters, scenes, notes,
research, worldbuilding, attachments, generated assets, embeddings, prompts, responses,
filesystem paths, raw logs, and identity.

DataForge does not accept, retrieve, index, embed, back up, or synchronize that material.
The historical AuthorForge ORM tables and CRUD modules in this repository are quarantined
legacy inventory. They are not mounted in `app.main` and must not be reactivated.

## Permitted Integration

The only permitted AuthorForge write is:

```text
POST /api/v1/events/authorforge-analytics
Content-Type: application/json
Authorization: Bearer <dedicated-authorforge-analytics-key>
```

The key must be database-backed and carry metadata with:

```json
{
  "service": "authorforge",
  "scopes": ["analytics:write"]
}
```

The request must validate as `AuthorForgeAnalyticsEnvelope.v1`. The contract is closed and
size-bounded. It permits coarse event/action/status/outcome enums; bounded counts, token usage,
duration, latency, and cost; provider/model identifiers; local/cloud execution classification;
receipt/evaluation versions; and prefix-constrained rotatable pseudonyms. It has no arbitrary
metadata container.

Rejected envelopes receive a generic `422` response. Rejected input is not echoed or logged.
Retries are idempotent by `event_id` and return `status=duplicate` after an accepted write.

## Prohibited Integration

- No shared PostgreSQL connection or schema for AuthorForge.
- No `/api/projects` calls; the whole family is a `410 Gone` tombstone.
- No content export, replication, backup, embedding, search indexing, or reconciliation in
  DataForge.
- No raw identifiers, user/account identity, file paths, raw logs, stack traces, prompts,
  responses, or free-form fields in analytics.
- No reuse of a general event, admin, or another service's API key.

## Legacy Metadata Audit

If an operator needs to determine whether historical AuthorForge tables may contain records,
run the read-only audit only after explicitly targeting the intended database:

```bash
DATAFORGE_DATABASE_URL=<reviewed-dsn> \
  .venv/bin/python scripts/audit_authorforge_boundary.py --max-ids-per-table 100
```

The audit selects only table existence, record counts, primary-key column names, and bounded
primary-key values. It never selects content columns and never mutates or deletes records.
Any remediation or disposition decision is a separate human-reviewed operation; this guide
does not authorize one.

## Verification

```bash
.venv/bin/pytest \
  tests/test_unit/test_authorforge_analytics.py \
  tests/test_unit/test_authorforge_boundary_audit.py -q
```

The canonical service boundary is maintained in `doc/system/` and compiled into
`doc/DTFSYSTEM.md` with `bash doc/system/BUILD.sh`.
