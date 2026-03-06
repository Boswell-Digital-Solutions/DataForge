# Forge Telemetry — System Documentation

**Document version:** 1.0 (2026-03-06) — Initial Forge Documentation Protocol v1 release
**Protocol:** Forge Documentation Protocol v1

This `doc/system/` tree uses explicit truth classes:
- Canonical facts define forge-telemetry's library role, supported service vocabulary, event model, environment resolution, and failure posture.
- Snapshot facts define audit-derived counts such as files, tests, or implementation inventory.

Repo deviation:
- forge-telemetry is a shared Python library, not a resident HTTP service or desktop app.

Assembly contract:
- Command: `bash doc/system/BUILD.sh`
- Output: `doc/ftSYSTEM.md`

| Part | File | Contents |
|------|------|----------|
| §1 | `01-overview-philosophy.md` | Library role, scope, invariants, failure posture |
| §2 | `02-architecture.md` | Package architecture, DB resolution, event write flow |
| §3 | `03-tech-stack.md` | Python/runtime dependencies and package metadata |
| §4 | `04-project-structure.md` | Repository layout and module responsibilities |
| §5 | `05-config-env.md` | Environment variables, connection resolution, runtime toggles |
| §6 | `06-handover.md` | Known limitations, maintenance cautions, operator notes |

*Last updated: 2026-03-06*
