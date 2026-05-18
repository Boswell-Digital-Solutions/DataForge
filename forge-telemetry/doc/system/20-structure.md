# §4 — Project Structure

## Repository Layout

```text
forge-telemetry/
├── CLAUDE.md              # Repo-local instructions for Codex / Claude work
├── SYSTEM.md              # Generated root reference (build artifact)
├── forge_telemetry/
│   ├── __init__.py         # Public exports and package version
│   ├── client.py           # TelemetryClient, DB resolution, event writes
│   └── models.py           # Pydantic event model and enums
├── src/forge_telemetry/    # Alternate package-layout mirror
├── doc/system/            # Forge Documentation Protocol v1 source docs
├── docs/                  # Architecture spec and roadmap
├── scripts/               # Context bundle loader
├── tests/                 # Reserved for package tests (currently empty)
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

---
