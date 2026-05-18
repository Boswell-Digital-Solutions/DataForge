# §2 — Architecture

## Package Map

The runtime surface is intentionally small:

- `forge_telemetry/client.py` — client lifecycle, connection resolution, and event writes
- `forge_telemetry/models.py` — Pydantic event model and enums
- `forge_telemetry/__init__.py` — public exports and package version

## Event Write Flow

```text
Caller
  -> TelemetryClient(...) or emit_event(...)
  -> resolve database URL
  -> create SQLAlchemy engine if enabled
  -> validate connectivity with SELECT 1
  -> construct TelemetryEvent
  -> insert row into events table
  -> return event_id
```

## Database Resolution Order

`TelemetryClient` resolves the target database in this order:

1. explicit `database_url` argument
2. `DATAFORGE_DATABASE_URL`
3. composed DSN from:
   - `DATABASE_BASE_URL`
   - `DATABASE_USER`
   - `DATABASE_PASSWORD`
   - `DATABASE_NAME`
   - optional `DATABASE_SSLMODE`

If none of those paths resolve and telemetry is not required, the client disables itself.

## Engine Behavior

- SQLAlchemy engine creation is synchronous.
- The client performs an immediate connectivity probe (`SELECT 1`) during initialization.
- A `SessionLocal` factory is created only when connectivity succeeds.

## Event Serialization Behavior

- PostgreSQL path writes timestamps via `NOW()` and passes metadata/metrics as structured values.
- SQLite path serializes `metadata` and `metrics` as JSON strings and uses `CURRENT_TIMESTAMP`.

SQLite support is an implementation fallback in the writer, not the primary documented operating mode.

## Async Boundary

`emit_async()` is currently not truly async. It delegates to the synchronous `emit()` path and exists as an async-compatible call surface for async codebases.

That behavior is an implementation limitation and should not be documented as non-blocking I/O.

---
