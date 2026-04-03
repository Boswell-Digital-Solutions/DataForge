# §6 — Handover & Constraints

## Current Limitations

1. `emit_async()` is a compatibility wrapper over the synchronous implementation. It does not provide true async database I/O.
2. The typed service vocabulary only includes `dataforge`, `neuroforge`, and `rake`.
3. There is no local test suite in this repo at the moment.
4. The library assumes the `events` table already exists and is compatible with its insert statements.

## Operational Cautions

- Do not describe this package as a telemetry backend. It is only a client.
- Do not claim non-blocking async behavior until `emit_async()` is implemented with real async DB transport.
- Do not broaden the service enum or severity semantics in docs without changing `models.py`.
- Do not present fail-open telemetry suppression as durable storage success.

## Maintenance Rules

- If connection resolution changes, update both `README.md` and §5.
- If the public export surface changes, update §4.
- If a test suite is added, document it as a snapshot fact rather than backfilling historical claims.

## Build

```bash
bash doc/system/BUILD.sh
```

Expected output:

```text
SYSTEM.md
```
