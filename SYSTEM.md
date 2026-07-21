# DataForge System Reference (Legacy Pointer)

This root file is retained only as a compatibility pointer. The canonical modular source is
`doc/system/`; the generated canonical artifact is `doc/DTFSYSTEM.md` (designation `DTF`).

Do not copy historical AuthorForge integration guidance from older revisions of this file.
AuthorForge's embedded database is the exclusive source of truth for its projects and all user
content. DataForge accepts only strict minimized `AuthorForgeAnalyticsEnvelope.v1` telemetry at
`POST /api/v1/events/authorforge-analytics`; `/api/projects` is a fail-closed `410 Gone`
tombstone.

Rebuild the canonical artifact with:

```bash
bash doc/system/BUILD.sh
```
