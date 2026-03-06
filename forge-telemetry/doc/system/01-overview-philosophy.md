# §1 — Overview & Philosophy

## Identity

forge-telemetry is a small shared Python library for emitting operational telemetry events into the Forge ecosystem events table. It is a library surface, not a resident service.

## Boundary

- It emits events; it does not own telemetry storage.
- It relies on an already-provisioned database target; it does not create schema or manage migrations.
- It does not expose an HTTP API.
- It does not replace DataForge as the durable truth store.

## Canonical Role

The library provides:

- a `TelemetryClient` for synchronous event emission
- an `emit_async()` compatibility method for async callers
- a top-level `emit_event()` convenience function
- a shared `TelemetryEvent` model plus constrained service/severity vocabularies

## Failure Doctrine

The library is fail-open by default:

- if no database configuration is present, it disables emission and returns generated event IDs without writing
- if the database connection cannot be established and telemetry is not required, it disables emission and logs a warning
- if `TELEMETRY_REQUIRED=true`, missing or unreachable database configuration becomes a hard failure

This means telemetry can be optional for callers unless they explicitly opt into required mode.

## Current Supported Service Vocabulary

The current canonical `ServiceType` enum only includes:

- `dataforge`
- `neuroforge`
- `rake`

If additional services need first-class telemetry typing, the library contract must change accordingly.
