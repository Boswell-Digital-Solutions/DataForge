# VibeForge Code Language Selector – Full Implementation Blueprint

## Overview
This Markdown contains the complete detailed implementation plan for the **Code Language Selector** feature inside VibeForge.  
It is suitable for internal documentation, GitHub repos, and development sprint planning.

---

# 1. Purpose & Goals
The Code Language Selector allows users to define which programming languages their project uses.  
This enables:
- Intelligent stack recommendations  
- Language-aware scaffolding  
- Correct file structures  
- Accurate test generation  
- Proper env schema generation  
- Precise AI-assisted code generation  
- Cleaner project configuration  
- Future policy enforcement (Pro/Enterprise tiers)

---

# 2. Languages Included at Launch
A total of **15 languages**, grouped to reduce cognitive load.

## Frontend (3)
- JavaScript / TypeScript  
- Svelte  
- Solid  

## Backend (5)
- Python  
- Node.js  
- Go  
- Rust  
- Java  

## Systems / Tooling (4)
- C  
- C++  
- Bash  
- SQL  

## Mobile / Modern (3)
- Dart  
- Kotlin  
- Swift  

These represent 99% of real-world development and align with VibeForge’s stack profiles.

---

# 3. Project Wizard Integration

## Wizard Steps:
1. Describe Project  
2. **Select Code Languages** ← new step  
3. Select Stack Profile  
4. Select Modules/Features  
5. Scaffolding Preview  
6. Icon / Brand Setup  
7. Export or Apply  

The Language Selector heavily influences the following steps.

---

# 4. UX / UI Design

## Layout
3-column layout inside the wizard step:

### Left: Categories
- Frontend  
- Backend  
- Systems  
- Mobile/Modern  

### Middle: Language Chips
Clickable tiles:
- On select → highlighted
- Tooltip explaining usage
- Shows approximate ecosystem support

### Right: Real-time Effects Panel
- Compatible stacks  
- Hidden stacks  
- Recommended stacks (ranked)  
- Language badge preview for the project  

---

# 5. Stack Advisor Integration (NeuroForge)

The Stack Advisor Agent receives:
- Selected languages  
- Project type  
- Priorities  
- Platform (Web/Desktop/Mobile/API/AI)  

### Stack Filtering Examples

**Python + TS**  
→ Recommend: SvelteKit + FastAPI

**Rust + Svelte + Desktop**  
→ Recommend: Tauri + Axum + SvelteKit

**Go only**  
→ Recommend: Gin/Fiber stack

**Swift**  
→ Recommend: iOS app structure

---

# 6. Scaffolding Engine Plan

The scaffolding system becomes language-aware.

For each language, define:
- File structure  
- Boilerplate templates  
- Testing frameworks  
- Env variable mappings  
- Lint/format rules  
- Sample code snippet  
- Doc blocks  
- CI/CD steps  
- Build instructions  

### Examples:

**Python:**
- `main.py`, routers, models  
- FastAPI boilerplate  
- Pytest structure  
- `pyproject.toml`

**Rust:**
- `main.rs`, Axum routing  
- Cargo setup  
- WASM optional module  

**TypeScript/Svelte:**
- SvelteKit layout  
- Tailwind config  
- Vitest tests  

**Go:**
- `main.go`  
- Gin/Fiber routing  
- Go modules  

---

# 7. Dev Automations Enhancements

Language-aware automations added:

### Examples:
- Generate tests for Python module  
- Create Rust Axum endpoint  
- Build Go API handler  
- Generate SQL schema  
- Build CI config for Rust/Python/TS  
- Auto-lint according to languages  

This makes VibeForge a true multi-language AI coding environment.

---

# 8. DataForge Integration
Store selected languages per project:

**Location:**  
`/projects/{id}/languages.json`

Allows:
- Regenerating scaffolding  
- Cross-feature memory  
- Multi-agent collaboration  

---

# 9. Monetization Integration

## Free Linux Version (Launch)
- All 15 languages  
- Limited scaffolding  
- Basic automations  
- Local LLM support  

## Pro Version
- Advanced scaffolding  
- Multi-language worker generation  
- Cloud AI-powered code generation  
- Cross-project type syncing  

## Enterprise
- Enforce coding standards  
- Language policy rules  
- On-prem AI routing  
- Custom templates per language  

---

# 10. Roadmap Timeline (2025 → Early 2026)

### Phase 1 — Design (2–3 weeks)
- JSON schema  
- UI sketches  
- Integration mapping  

### Phase 2 — Core Coding (3–5 weeks)
- Build selector component  
- Integrate with Project Wizard  
- Connect to Stack Advisor  

### Phase 3 — Templates (4–8 weeks)
- Create per‑language scaffolding templates  
- Generate lint/test/CI templates  

### Phase 4 — AI Integration (3–6 weeks)
- Update Advisor + Automation prompts  

### Phase 5 — QA + Pre-Release (Jan 2026)
- Testing  
- Freeze for Linux release  

### Release: Early January 2026

---

# 11. Files Produced By This System

### At project creation:
- `/languages.json`  
- Language badges in `README.md`  
- Language-specific folders  
- Tests per language  
- CI pipeline tuned to selected languages  
- Dockerfiles that match project languages  

---

# 12. Future Extensions

### Add languages:
- Zig  
- Elixir  
- Ruby  
- PHP  
- Lua  
- Haskell  

### Add advanced modes:
- Language policy enforcement  
- Stack-Language compatibility matrix  

### Add team features:
- Shared language presets  
- Project templates  
- Team governance rules  

---

# END OF DOCUMENT
