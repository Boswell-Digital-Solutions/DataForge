# forge-telemetry — Claude Code Context

## Project Identity

- **What it is:** Shared Python telemetry library for Forge services
- **Authority boundary:** Event-model and emission helper ownership only; not a resident service and not the durable truth store
- **Primary package:** `forge_telemetry/`
- **Primary entrypoints:** `forge_telemetry/client.py`, `forge_telemetry/models.py`

## Module Map

```text
forge-telemetry/
├── forge_telemetry/        # Published package surface
├── src/forge_telemetry/    # Alternate package-layout mirror
├── doc/system/             # Modular system reference source
├── docs/                   # Architecture spec and roadmap
├── scripts/                # Context bundle loader
├── tests/                  # Reserved for package tests (currently empty)
├── README.md               # Library overview
├── setup.py                # Packaging metadata
└── requirements.txt        # Runtime dependencies
```

## Coding Standards

- Python 3.9+ compatible
- Keep `TelemetryClient` fail-open by default unless `TELEMETRY_REQUIRED=true`
- Do not introduce resident-service semantics into this repo
- Treat `forge_telemetry.__all__` as the public contract; update docs if exports change
- Keep event writes aligned with the shared `events` table contract described in `SYSTEM.md`

## Context Loading

```bash
bash doc/system/BUILD.sh
./scripts/context-bundle.sh --list
./scripts/context-bundle.sh --dry-run --preset core
./scripts/context-bundle.sh --dry-run --preset config
./scripts/context-bundle.sh --dry-run --preset handover
```

Root `SYSTEM.md` is the primary assembled reference. Legacy `doc/ftSYSTEM.md` remains mirrored
for compatibility.

## Change Protocol

1. Update `doc/system/02-architecture.md` when changing emission flow or DB resolution.
2. Update `doc/system/04-project-structure.md` when moving files or adding modules.
3. Update `doc/system/05-config-env.md` when changing env vars or fail-open/fail-closed behavior.
4. If package behavior changes, add tests under `tests/` rather than leaving the repo testless.
5. Keep this repo documented as a library boundary, not as part of the parent DataForge runtime.
