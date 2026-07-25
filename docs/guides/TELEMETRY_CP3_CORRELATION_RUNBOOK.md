# CP3 Telemetry Correlation Read Runbook

**Status:** Candidate pending CP3 Triple Proof acceptance

DataForge owns the canonical shared-event side of CP3 correlation. The only
new read surface is:

```text
GET /api/v1/telemetry/correlations/{canonical-uuid}
    ?environment={exact-environment}
    &tenant_ref={exact-tenant-or-omitted}
```

The endpoint is disabled by default. Enable it only after the CP3 human
checkpoint:

```text
DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED=true
```

## Reader identity

Create a dedicated API key with metadata exactly equivalent to:

```json
{
  "service_name": "forge_command",
  "environment": "development",
  "tenant_ref": "bds-internal",
  "scopes": ["telemetry:read"]
}
```

Use `null` rather than an omitted metadata field when the deployment has no
tenant. Do not reuse a producer key. Add `telemetry:read:restricted` only after
separate approval for classified trace linkage.

## Read guarantees

- The projection never contains `attributes` or `metrics`.
- A correlation ID observed under another environment or tenant fails closed
  with `correlation_scope_conflict`.
- Missing trace linkage and unsampled events are explicit.
- Restricted and confidential event types and trace identifiers are redacted
  unless the key has the restricted-read scope.
- Results are ordered and bounded to 200 events and 256 KiB. An additional
  matching event or response-byte truncation makes `shared_state=partial`; the
  endpoint never implies completeness.
- Database or configuration failure returns a stable unavailable response.

## Rollback

Set `DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED=false`, restart DataForge,
and remove `DATAFORGE_TELEMETRY_READ_KEY` from Forge_Command. This disables the
shared drill-through path without deleting canonical events or local spans.
Do not restore a legacy telemetry path and do not rewrite historical trace
fields.
