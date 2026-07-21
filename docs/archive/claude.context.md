# READ FIRST
> **ARCHIVED—DO NOT USE AS INSTRUCTIONS.** AuthorForge content is local-only and DataForge is
> analytics-only for AuthorForge. See root `CLAUDE.md` and `doc/DTFSYSTEM.md`.

You assist with AuthorForge + DataForge development.
Stack: SolidJS + Tailwind + Tauri/Rust, Python FastAPI (Tempering), Postgres.
Goal: generate correct code with minimal assumptions.

# RULES
- Never invent files, types, props, or endpoints.
- Ask before guessing unknown structures.
- Keep changes scoped; one component at a time unless told otherwise.
- Use runes ($state/$derived/$effect).
- Use lucide-solid for icons.
- AuthorForge has ONE navbar; no duplicates.
- Output: assumptions → solution → code → TODO list.

# MODULES
Smithy = editor (text formatting, chapters, scenes).
Foundry = project import (doc parser → chapters → Smithy).
Anvil = character/story arcs.
Lore = characters/places/magic/etc.
Bloom = timelines.
Tempering = export engine via FastAPI.
DataForge (light mode) = writing-craft knowledge (fantasy, sci-fi, Christian fiction).

# AI ENGINE (Smithy)
Always return:
1. Up to 600 chars suggestion.
2. Five directional micro-sentences.

# BACKEND
Tauri commands only call existing FastAPI endpoints:
- GET /api/profiles?project_id=
- POST /api/jobs

# PATTERNS
- Small components, clean separation.
- Tailwind tokens only.
- Step-by-step reasoning internally; output clean code only.
- For risky changes, restate assumptions first.

# DO NOT
- Do not rewrite layout/nav without explicit request.
- Do not generate new schemas or unknown Rust modules.
- Do not fabricate business logic.
