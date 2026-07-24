# Render Supabase Log Poller Runbook

## Incident assessment (2026-07-20)

The repository contains no Render API credential, CLI session, or exported job log, so the
production failure's first error line and phase (build versus run) could not be observed. Do not
describe the production root cause as confirmed until that evidence is available.

The repository does prove one deterministic deployment defect: `render.yaml` previously attached
an SSH-named environment group and documented `SSH_KEY`/`SSH_KEY_B64`, while
`scripts/render-git-auth.sh` requires `FORGE_TELEMETRY_TOKEN` or `GITHUB_TOKEN` and exits on
Render when neither is present. If the service environment matched the blueprint documentation,
the build failed before dependency installation. That is a confirmed code/config mismatch and a
likely incident cause, not proof of the actual last job state.

The previous runtime also had independent hazards:

- it called the deprecated `logs.all` endpoint;
- it omitted the required explicit timestamp-window parameters;
- it did not distinguish authentication, authorization, rate-limit, network, payload, database,
  or missing-migration failures;
- it did not verify `supabase_log_events` before polling; and
- the cron build did not establish a documented migration ownership strategy.

## Applied repair

- Both Render services now declare the same build-only `FORGE_TELEMETRY_TOKEN`; SSH variables are
  not consumed.
- `scripts/render-cron-build.sh` installs dependencies, requires exactly one Alembic head, and
  compiles imports. It never runs migrations.
- The web build remains the sole Render migration runner (`alembic upgrade head`). The poller
  performs a read-only connectivity/table preflight and exits with
  `database_migration_failure/supabase_log_events_table_missing` when the web migration has not
  completed.
- The poller uses Supabase's current unified
  `/v1/projects/{ref}/analytics/endpoints/logs` endpoint with source-filtered ClickHouse SQL,
  Bearer authentication, both ISO timestamp parameters, and a window below 24 hours.
- SQL projects only `id`, `timestamp`, `event_message`, and `source AS log_type`. The existing
  redaction/allow-list pipeline runs before idempotent persistence by source log ID.
- Logs contain only stable categories/codes and aggregate counts. Tokens, URLs containing
  credentials, upstream bodies, raw exceptions, input filenames, and raw event content are not
  logged.

Supabase's current contract requires the `analytics:read` OAuth scope or
`analytics_logs_read` fine-grained permission, limits a query window to 24 hours, and documents
402/401/403/429 responses for the unified endpoint. See the
[Management API reference](https://supabase.com/docs/reference/api/introduction) and
[logging/query reference](https://supabase.com/docs/guides/telemetry/logs).

## Required Render variable names

Web and cron build:

- `FORGE_TELEMETRY_TOKEN` (preferred) or `GITHUB_TOKEN` fallback; read-only access to the two
  pinned private dependencies.

Cron runtime:

- `DATAFORGE_DATABASE_URL`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_LOG_IDENTITY_SALT` (recommended; raw identity is dropped when absent)
- `SUPABASE_LOG_SOURCE_TABLE` (default `edge_logs`)

Never place values in tickets, chat, screenshots, or logs. Confirm names and presence only.

## Safe verification

After deploying the web migration and then the cron build:

```bash
python -m scripts.poll_supabase_logs --preflight-only
python -m scripts.poll_supabase_logs --once
```

Expected successful messages report only preflight components and counts. A retry over the same
window must increase `duplicates` rather than insert the same source ID twice.

Failure output is one of:

| Category | Typical codes |
|----------|---------------|
| `configuration` | missing/invalid DB URL, project ref, token, source, limit, lookback, overlap |
| `authentication` | `supabase_token_rejected` |
| `authorization` | missing log permission or required plan |
| `rate_limiting` | `supabase_logs_rate_limited` |
| `network_failure` | `supabase_api_unreachable` |
| `upstream_failure` | missing project/endpoint or Supabase 5xx |
| `payload_schema_failure` | rejected query or unexpected response shape |
| `database_failure` | connectivity/schema-check/write failure |
| `database_migration_failure` | `supabase_log_events_table_missing` |

## Evidence still needed from the failed production job

Provide only sanitized operational evidence:

1. Whether the last failure occurred during **Build** or **Run**.
2. The first sanitized error line, or the new `category` and `code` after deployment.
3. Whether these variable names exist on the cron service (presence only):
   `FORGE_TELEMETRY_TOKEN`, `DATAFORGE_DATABASE_URL`, `SUPABASE_PROJECT_REF`,
   `SUPABASE_ACCESS_TOKEN`, `SUPABASE_LOG_IDENTITY_SALT`.
4. Whether the web service successfully applied the migration containing
   `supabase_log_events`, plus the current Alembic revision identifier. Do not query or paste
   stored log rows.

## AuthorForge boundary

This poller is for redacted Supabase operational/security evidence. It is not an AuthorForge
content path. Do not add AuthorForge manuscripts, notes, prompts/responses, paths, raw logs,
embeddings, attachments, or identity to its query or storage model. Potential legacy AuthorForge
records may be assessed only with `scripts/audit_authorforge_boundary.py`, which reads IDs,
counts, and categories without selecting content columns or mutating data. The audit also flags
historical `pf_*` tables with explicit AuthorForge links or content-capable fields for a human
ownership review; it does not classify their rows as violations automatically.
