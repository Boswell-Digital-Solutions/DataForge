# §5 — Configuration & Environment

## Canonical Inputs

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATAFORGE_DATABASE_URL` | No | Primary DSN for direct connection resolution |
| `DATABASE_BASE_URL` | No | Host/base input for composed DSN |
| `DATABASE_USER` | No | Username for composed DSN |
| `DATABASE_PASSWORD` | No | Password for composed DSN |
| `DATABASE_NAME` | No | Database name for composed DSN |
| `DATABASE_SSLMODE` | No | SSL mode for composed DSN; defaults to `require` |
| `TELEMETRY_REQUIRED` | No | Hardens missing/unreachable DB into a startup error |

## Resolution Semantics

- explicit constructor `database_url` wins
- then `DATAFORGE_DATABASE_URL`
- then composed DSN from component variables
- otherwise telemetry remains disabled unless required mode is active

## Constructor Contract

```python
TelemetryClient(
    database_url: Optional[str] = None,
    *,
    telemetry_required: Optional[bool] = None,
)
```

`telemetry_required` can be set explicitly or inherited from `TELEMETRY_REQUIRED`.

## Example

```bash
export DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
export TELEMETRY_REQUIRED=false
```

## Important Distinction

The library currently reads `DATAFORGE_DATABASE_URL`, not the broader ecosystem's mixed service URL vocabulary. That is a local library contract and should not be confused with resident service configuration.
