# §4 — Project Structure

## Repository Layout

```text
forge-telemetry/
├── forge_telemetry/
│   ├── __init__.py         # Public exports and package version
│   ├── client.py           # TelemetryClient, DB resolution, event writes
│   └── models.py           # Pydantic event model and enums
├── doc/system/            # Forge Documentation Protocol v1 source docs
├── README.md              # Repo entrypoint overview
├── requirements.txt       # Runtime dependencies
└── setup.py               # Packaging metadata
```

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `forge_telemetry.client` | Connection resolution, fail-open handling, inserts into `events` |
| `forge_telemetry.models` | Shared enums and `TelemetryEvent` model |
| `forge_telemetry.__init__` | Stable import surface |

## Public Import Surface

The package currently exports:

- `TelemetryClient`
- `emit_event`
- `TelemetryEvent`
- `ServiceType`
- `SeverityLevel`

Consumers should treat that export list as the intended public interface unless the package contract changes.
