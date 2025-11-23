# VibeForge Automation - Implementation Plan

**Date:** November 22, 2025  
**Status:** 📋 Planning Phase  
**Blueprint Source:** `vibeforge_automation_blueprint_full.md`

---

## 🎯 Executive Summary

This plan breaks down the VibeForge Automation Blueprint into **5 major phases** with **29 total milestones** spanning approximately **17-21 weeks** of development. Each phase builds on the previous one, creating a complete AI-powered project automation system.

### Key Deliverables

1. **Stack Profile System** - 10 modern stack templates with language support
2. **Language Selector** - 15-language multi-select system (NEW)
3. **Project Creation Wizard** - Full-screen 7-step guided project setup
4. **Stack Advisor Agent** - AI-powered language-aware recommendations
5. **Icon Lab** - SVG generation and icon pack creation
6. **Dev Automations** - Language-aware feature/test/docs/CI generators

---

## 📊 Phase Overview

| Phase       | Focus                           | Duration | Complexity | Dependencies        |
| ----------- | ------------------------------- | -------- | ---------- | ------------------- |
| **Phase 1** | Stack Profile & Language System | 3 weeks  | Medium     | None (start here)   |
| **Phase 2** | Project Creation Wizard         | 5 weeks  | High       | Phase 1             |
| **Phase 3** | Stack Advisor Agent             | 3 weeks  | Medium     | Phase 1, NeuroForge |
| **Phase 4** | Icon Lab                        | 3 weeks  | Medium     | NeuroForge          |
| **Phase 5** | Dev Automations                 | 4 weeks  | High       | Phase 1, 2, 3       |

**Total Estimated Time:** 17-21 weeks (4-5 months)

---

## 🔧 Current System State

### ✅ Already Complete

- VibeForge frontend architecture (SvelteKit, 3-column layout)
- NeuroForge LLM orchestration (OpenAI, Anthropic, Ollama)
- DataForge knowledge base (semantic search, embeddings)
- JWT authentication system
- Multi-provider LLM execution
- Basic UI component library

### 🚧 Needs Implementation

- Stack profile definitions and storage
- **Language selector system (15 languages)**
- **Language-aware scaffolding engine**
- Project scaffolding templates
- File generation system
- SVG generation capabilities
- Icon pack generation
- **Multi-language automation workflows**

---

# Phase 1: Stack Profile System (3 weeks)

**Goal:** Define, store, and manage 7-8 modern stack profiles that drive all automation features.

---

## Milestone 1.1: Stack Profile Schema (3 days)

### Tasks

1. Design stack profile data model
2. Create TypeScript interfaces
3. Create Pydantic models (NeuroForge)
4. Design database schema (DataForge)

### Deliverables

```typescript
interface StackProfile {
  id: string;
  name: string;
  description: string;
  category: "web" | "mobile" | "desktop" | "api" | "ai";

  technologies: {
    frontend?: Technology[];
    backend?: Technology[];
    database?: Technology[];
    infrastructure?: Technology[];
  };

  features: string[];
  requirements: {
    complexity: "beginner" | "intermediate" | "advanced";
    timeToMarket: "fast" | "medium" | "slow";
    scalability: "low" | "medium" | "high";
  };

  envSchema: EnvVariable[];
  scaffolding: ScaffoldingTemplate;
  documentation: DocumentationTemplate;
}
```

### Files to Create

- `/vibeforge/src/lib/core/types/stack-profiles.ts`
- `/NeuroForge/neuroforge_backend/models/stack_models.py`
- `/DataForge/app/models/stack_profiles.py`

---

## Milestone 1.2: Stack Profile Definitions (5 days)

### Tasks

1. Define all 7 stack profiles in JSON/YAML
2. Create template files for each stack
3. Document stack characteristics
4. Create comparison matrices

### Stack Profiles to Define

1. **Forge Web Stack** (SvelteKit + FastAPI + Postgres)
2. **Next.js Full Stack** (Next.js + Node/FastAPI)
3. **Mobile App Stack** (React Native + Expo)
4. **Python AI Stack** (FastAPI + Celery + Redis)
5. **Node.js Backend** (NestJS/Express + MongoDB)
6. **Golang Cloud-Native** (Gin/Fiber + Postgres)
7. **Rust Native Stack** (Axum/Actix + Tauri)
8. **SolidStart Performance** (Optional)

### Files to Create

- `/vibeforge/src/lib/data/stack-profiles/forge-web.json`
- `/vibeforge/src/lib/data/stack-profiles/nextjs-fullstack.json`
- (... 5 more stack files)
- `/vibeforge/src/lib/data/stack-profiles/index.ts`

---

## Milestone 1.3: Stack Profile API (4 days)

### Tasks

1. Create DataForge endpoints for stack profiles
2. Implement CRUD operations
3. Add search/filter functionality
4. Create caching layer

### Endpoints to Create

```
GET    /api/v1/stacks              # List all stacks
GET    /api/v1/stacks/{id}         # Get specific stack
POST   /api/v1/stacks/search       # Search stacks by criteria
GET    /api/v1/stacks/compare      # Compare multiple stacks
POST   /api/v1/stacks              # Create custom stack (admin)
```

### Files to Create

- `/DataForge/app/routers/stacks.py`
- `/DataForge/app/services/stack_service.py`
- `/DataForge/app/repositories/stack_repository.py`

---

## Milestone 1.4: Language Data Models & Storage (2 days)

**Reference:** `vibeforge_language_selector_blueprint.md` (Section 8 - DataForge Integration)

### Tasks

1. Create language data models
2. Define language compatibility matrices
3. Set up project language storage
4. Create language preference API

### Data Models

```typescript
interface Language {
  id: string;
  name: string;
  category: "frontend" | "backend" | "systems" | "mobile";
  icon: string;
  compatibleStacks: string[];
  scaffoldingSupport: boolean;
}

interface ProjectLanguages {
  projectId: string;
  languages: string[];
  primary: string;
  createdAt: string;
  updatedAt: string;
}
```

### Storage Location

`/projects/{id}/languages.json` in DataForge

This enables:

- Regenerating language-aware scaffolding
- Cross-feature memory
- Multi-agent collaboration
- Language preference tracking

### Files to Create

- `/DataForge/app/models/project_languages.py`
- `/DataForge/app/routers/project_languages.py`
- `/vibeforge/src/lib/data/languages.ts`
- `/NeuroForge/neuroforge_backend/models/language_models.py`

---

## Milestone 1.5: Stack Profile UI Components (3 days)

### Tasks

1. Create StackCard component
2. Create StackComparisonTable component
3. Create StackSelector component
4. Add to Storybook (if using)

### Components to Create

- `/vibeforge/src/lib/ui/components/StackCard.svelte`
- `/vibeforge/src/lib/ui/components/StackComparison.svelte`
- `/vibeforge/src/lib/ui/components/StackSelector.svelte`

---

# Phase 2: Project Creation Wizard (4 weeks)

**Goal:** Build the full-screen project creation overlay with 6-step wizard flow.

---

## Milestone 2.1: Wizard Architecture (5 days)

### Tasks

1. Design wizard state machine
2. Create wizard navigation system
3. Implement step validation
4. Add progress tracking

### Architecture Components

- Wizard store (Svelte store)
- Step routing system
- Validation engine
- Progress persistence

### Files to Create

- `/vibeforge/src/lib/core/stores/wizardStore.ts`
- `/vibeforge/src/lib/core/types/wizard.ts`
- `/vibeforge/src/routes/wizard/+layout.svelte`

---

## Milestone 2.2: Step 1 - Project Intent (3 days)

### Tasks

1. Build project description form
2. Add project type selector
3. Add priority toggles
4. Implement AI-powered intent parsing

### UI Components

- Project name/description input
- Type selector (web/mobile/desktop/api/ai)
- Priority matrix (time/performance/safety/local/ai)
- Intent summary preview

### Files to Create

- `/vibeforge/src/routes/wizard/step-1/+page.svelte`
- `/vibeforge/src/lib/ui/wizard/ProjectIntentForm.svelte`

---

## Milestone 2.3: Step 2 - Language Selector (4 days)

**Reference:** `vibeforge_language_selector_blueprint.md`

### Tasks

1. Build language selection UI with categories
2. Implement multi-select functionality
3. Create real-time stack filtering
4. Add language-specific recommendations
5. Generate language badge previews

### UI Layout (3-column)

**Left Panel:** Language Categories

- Frontend (JavaScript/TypeScript, Svelte, Solid)
- Backend (Python, Node.js, Go, Rust, Java)
- Systems/Tooling (C, C++, Bash, SQL)
- Mobile/Modern (Dart, Kotlin, Swift)

**Center Panel:** Language Chips

- Clickable selection tiles
- Tooltips with ecosystem info
- Visual feedback on selection

**Right Panel:** Real-time Effects

- Compatible stacks list
- Hidden/incompatible stacks
- Ranked recommendations
- Language badge preview

### Integration Points

- Stack Advisor (filters by languages)
- Scaffolding Engine (language-aware templates)
- Project metadata storage (DataForge)

### Language Definitions

Total of **15 languages** at launch:

- **Frontend:** JavaScript/TypeScript, Svelte, Solid
- **Backend:** Python, Node.js, Go, Rust, Java
- **Systems:** C, C++, Bash, SQL
- **Mobile:** Dart, Kotlin, Swift

### Files to Create

- `/vibeforge/src/routes/wizard/step-2/+page.svelte`
- `/vibeforge/src/lib/ui/wizard/LanguageSelector.svelte`
- `/vibeforge/src/lib/ui/wizard/LanguageChip.svelte`
- `/vibeforge/src/lib/ui/wizard/LanguageEffectsPanel.svelte`
- `/vibeforge/src/lib/data/languages.ts` (language definitions)
- `/vibeforge/src/lib/core/types/languages.ts` (TypeScript types)

### Data Models

```typescript
interface Language {
  id: string;
  name: string;
  category: "frontend" | "backend" | "systems" | "mobile";
  icon: string;
  color: string;
  description: string;
  ecosystemSupport: "excellent" | "good" | "moderate";
  compatibleStacks: string[]; // stack IDs
  scaffoldingTemplates: string[]; // template IDs
}

interface ProjectLanguages {
  selected: string[]; // language IDs
  primary?: string; // main language
  timestamp: string;
}
```

---

## Milestone 2.4: Step 3 - Stack Selection (4 days)

### Tasks

1. Display ranked stack recommendations
2. Show pros/cons for each stack
3. Allow manual override
4. Show stack comparison

### Integration Points

- Stack Advisor Agent (NeuroForge)
- Stack Profile API (DataForge)

### Files to Create

- `/vibeforge/src/routes/wizard/step-2/+page.svelte`
- `/vibeforge/src/lib/ui/wizard/StackRecommendations.svelte`

---

## Milestone 2.5: Step 4 - Module Selection (4 days)

### Tasks

1. Display module checklist (frontend/backend/features)
2. Show dependencies between modules
3. Calculate package requirements
4. Preview directory structure

### Module Categories

- **Frontend:** Auth, Dashboard, Settings, Theme, Router
- **Backend:** API, Health, Workers, Database
- **Forge:** NeuroForge, DataForge, Pattern Library

### Files to Create

- `/vibeforge/src/routes/wizard/step-3/+page.svelte`
- `/vibeforge/src/lib/ui/wizard/ModuleSelector.svelte`

---

## Milestone 2.6: Step 5 - Scaffolding Preview (5 days)

### Tasks

1. Build three-panel layout
2. Generate file tree
3. Generate actual code files
4. Generate documentation
5. Add copy-to-clipboard

### Preview Panels

- **Left:** File tree with folder structure
- **Center:** Code preview with syntax highlighting
- **Right:** Documentation (SETUP.md, ARCHITECTURE.md)

### Files to Create

- `/vibeforge/src/routes/wizard/step-4/+page.svelte`
- `/vibeforge/src/lib/ui/wizard/ScaffoldingPreview.svelte`
- `/vibeforge/src/lib/ui/wizard/FileTree.svelte`
- `/vibeforge/src/lib/ui/wizard/CodePreview.svelte`

---

## Milestone 2.7: Step 6 - Icon & Brand (3 days)

### Tasks

1. Integrate Icon Lab (Phase 4)
2. Add brand color picker
3. Preview icon in context
4. Generate brand assets

### Files to Create

- `/vibeforge/src/routes/wizard/step-5/+page.svelte`
- `/vibeforge/src/lib/ui/wizard/BrandSetup.svelte`

---

## Milestone 2.8: Step 7 - Apply/Export (3 days)

### Tasks

1. Add download ZIP option
2. Add copy-to-clipboard option
3. Add local apply (MCP/Tauri)
4. Store project metadata in DataForge

### Export Options

1. Download project.zip
2. Copy individual files
3. Apply to local filesystem
4. Save to DataForge for future reference

### Files to Create

- `/vibeforge/src/routes/wizard/step-6/+page.svelte`
- `/vibeforge/src/lib/services/projectExport.ts`

---

## Milestone 2.9: Scaffolding Engine (Backend) (5 days)

**Reference:** `vibeforge_language_selector_blueprint.md` (Section 6 - Scaffolding Engine Plan)

### Tasks

1. Create template rendering engine
2. Implement language-aware file generation
3. Add env schema generation
4. Create ZIP packaging service
5. Build language-specific template system

### Engine Capabilities

- Jinja2/Handlebars template rendering
- Language-aware file tree generation
- Package.json/requirements.txt/Cargo.toml generation (per language)
- Docker/docker-compose generation (multi-language support)
- README/docs generation
- **Language-specific boilerplate generation**

### Language-Aware Templates

For each supported language, define:

- File structure patterns
- Boilerplate code templates
- Testing framework setup
- Linting/formatting configuration
- Build instructions
- CI/CD pipeline templates
- Documentation blocks

**Example Language Templates:**

**Python:**

- `main.py`, routers, models structure
- FastAPI boilerplate
- pytest configuration
- `pyproject.toml`, `requirements.txt`
- Black/Flake8 config

**Rust:**

- `main.rs`, Axum routing
- Cargo.toml setup
- WASM optional module
- Clippy configuration

**TypeScript/Svelte:**

- SvelteKit layout
- Tailwind config
- Vitest tests
- tsconfig.json

**Go:**

- `main.go`
- Gin/Fiber routing
- Go modules
- Golint setup

### Files to Create

- `/NeuroForge/neuroforge_backend/scaffolding/engine.py`
- `/NeuroForge/neuroforge_backend/scaffolding/language_templates/` (per-language directories)
- `/NeuroForge/neuroforge_backend/scaffolding/templates/`
- `/NeuroForge/neuroforge_backend/scaffolding/generators/`
- `/NeuroForge/neuroforge_backend/scaffolding/language_registry.py`

---

# Phase 3: Stack Advisor Agent (3 weeks)

**Goal:** Build AI-powered stack recommendation system using NeuroForge.

---

## Milestone 3.1: Stack Advisor Prompt Engineering (4 days)

**Reference:** `vibeforge_language_selector_blueprint.md` (Section 5 - Stack Advisor Integration)

### Tasks

1. Design advisor prompts with language awareness
2. Create evaluation criteria
3. Build scoring system
4. Implement language-based stack filtering
5. Test with various language combinations

### Advisor Input Parameters

- Selected programming languages
- Project type (web/mobile/desktop/api/ai)
- Platform targets
- Performance priorities
- Team size and expertise

### Language-Based Stack Filtering Examples

**Python + TypeScript:**
→ Recommend: SvelteKit + FastAPI, Next.js + Django

**Rust + Svelte + Desktop:**
→ Recommend: Tauri + Axum + SvelteKit

**Go only:**
→ Recommend: Gin/Fiber stack, Templ + HTMX

**Swift:**
→ Recommend: iOS native structure

**Java + React:**
→ Recommend: Spring Boot + React stack

### Scoring Criteria

- **Language compatibility (30%)** - Stack matches selected languages
- Technical fit (25%)
- Team expertise match (15%)
- Time-to-market alignment (15%)
- Scalability requirements (10%)
- Cost considerations (5%)

### Files to Create

- `/NeuroForge/neuroforge_backend/agents/stack_advisor.py`
- `/NeuroForge/neuroforge_backend/agents/language_stack_filter.py`
- `/NeuroForge/prompts/stack_advisor_system.txt`
- `/NeuroForge/prompts/stack_advisor_user.txt`
- `/NeuroForge/prompts/language_aware_recommendation.txt`

---

## Milestone 3.2: Stack Comparison Engine (3 days)

### Tasks

1. Build stack comparison matrix
2. Calculate similarity scores
3. Generate pros/cons
4. Create explanation generator

### Files to Create

- `/NeuroForge/neuroforge_backend/services/stack_comparison.py`

---

## Milestone 3.3: Stack Advisor API (3 days)

### Tasks

1. Create advisor endpoints
2. Add caching for common queries
3. Implement rate limiting
4. Add logging/analytics

### Endpoints to Create

```
POST   /api/v1/advisor/recommend   # Get stack recommendations
POST   /api/v1/advisor/compare     # Compare specific stacks
POST   /api/v1/advisor/explain     # Explain recommendation
```

### Files to Create

- `/NeuroForge/neuroforge_backend/routers/advisor_router.py`

---

## Milestone 3.4: Stack Advisor UI Integration (4 days)

### Tasks

1. Integrate advisor into wizard
2. Display recommendations with explanations
3. Add interactive comparison tool
4. Show confidence scores

### Files to Create

- `/vibeforge/src/lib/core/api/advisorClient.ts`
- `/vibeforge/src/lib/ui/wizard/AdvisorRecommendations.svelte`

---

## Milestone 3.5: Learning System (Optional) (3 days)

### Tasks

1. Track user selections vs recommendations
2. Store feedback in DataForge
3. Improve recommendations over time
4. Generate stack usage analytics

---

# Phase 4: Icon Lab (3 weeks)

**Goal:** Build SVG generation, upload conversion, and icon pack generation system.

---

## Milestone 4.1: SVG Generator (NeuroForge) (5 days)

### Tasks

1. Create SVG generation prompts
2. Build SVG validator
3. Implement style templates
4. Add color palette system

### SVG Styles

- Minimal
- Flat
- Outline
- 3D-lite
- Forge theme (default)

### Files to Create

- `/NeuroForge/neuroforge_backend/services/svg_generator.py`
- `/NeuroForge/prompts/svg_generator_system.txt`

---

## Milestone 4.2: Image Upload & Vectorization (4 days)

### Tasks

1. Integrate potrace/sharp for tracing
2. Build upload handler
3. Create SVG cleanup pipeline
4. Add AI-powered refinement

### Supported Formats

- PNG
- JPG
- SVG
- WEBP
- AVIF

### Files to Create

- `/NeuroForge/neuroforge_backend/services/image_vectorizer.py`
- `/vibeforge/src/lib/services/imageUpload.ts`

---

## Milestone 4.3: Icon Pack Generator (4 days)

### Tasks

1. Generate favicon.ico
2. Generate PNG sizes (16-512px)
3. Generate apple-touch-icon
4. Generate webmanifest
5. Create component files (Svelte/React/Vue)

### Generated Assets

- `favicon.ico`
- `favicon.svg`
- `icon-{16,32,64,128,256,512}.png`
- `apple-touch-icon.png`
- `mask-icon.svg`
- `site.webmanifest`
- `Icon.svelte` (component)
- `brand.json` (metadata)
- `README_LOGO.md` (usage instructions)

### Files to Create

- `/NeuroForge/neuroforge_backend/services/icon_pack_generator.py`

---

## Milestone 4.4: Icon Lab UI (4 days)

### Tasks

1. Build Icon Lab interface
2. Add preview thumbnails
3. Create context preview (browser tab, sidebar, button)
4. Add download/export options

### UI Components

- Icon description form
- Upload dropzone
- Size preview strip (16-512px)
- Theme preview (dark/light/accent)
- Context preview (favicon, nav, button)
- Export panel

### Files to Create

- `/vibeforge/src/routes/icon-lab/+page.svelte`
- `/vibeforge/src/lib/ui/icon-lab/IconPreview.svelte`
- `/vibeforge/src/lib/ui/icon-lab/IconUpload.svelte`
- `/vibeforge/src/lib/ui/icon-lab/IconExport.svelte`

---

## Milestone 4.5: Thumbnail System (2 days)

### Tasks

1. Create thumbnail generator
2. Build preview components
3. Add side-by-side comparison
4. Generate all preview contexts

### Files to Create

- `/vibeforge/src/lib/ui/components/IconThumbnail.svelte`
- `/vibeforge/src/lib/ui/components/IconContextPreview.svelte`

---

# Phase 5: Dev Automations (4 weeks)

**Goal:** Build feature/test/docs/CI generation tools.

---

## Milestone 5.1: Feature Module Generator (5 days)

**Reference:** `vibeforge_language_selector_blueprint.md` (Section 7 - Dev Automations Enhancements)

### Tasks

1. Build language-aware module template system
2. Generate routes/components per language
3. Generate API endpoints per language
4. Generate language-specific tests
5. Update documentation

### Language-Aware Generation

The generator adapts based on selected project languages:

**Python Projects:**

- FastAPI routers, Pydantic models
- Pytest test files
- Python docstrings

**TypeScript Projects:**

- SvelteKit routes, TypeScript types
- Vitest test files
- JSDoc/TSDoc comments

**Go Projects:**

- Gin/Fiber handlers
- Go test files
- Go doc comments

**Rust Projects:**

- Axum routers, Rust structs
- Cargo test modules
- Rustdoc comments

### Generated Files per Feature (Language-Aware)

- Frontend routes (if frontend language selected)
- Language-specific components
- Backend endpoints (in project's backend language)
- Database models (language-specific ORM)
- Language-appropriate tests
- Updated README with language badges
- Updated ROUTES.md

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/feature_generator.py`
- `/NeuroForge/neuroforge_backend/generators/language_templates.py`
- `/vibeforge/src/routes/automations/feature-generator/+page.svelte`

---

## Milestone 5.2: Test Generator (4 days)

**Reference:** `vibeforge_language_selector_blueprint.md` (Section 7)

### Tasks

1. Generate language-specific unit tests
2. Generate integration tests
3. Generate E2E tests per language
4. Generate API contract tests

### Language-Specific Test Frameworks

**Python:** pytest, pytest-asyncio
**TypeScript:** Vitest, Playwright
**Go:** Go test, testify
**Rust:** cargo test, rstest
**Java:** JUnit, Mockito

### Test Types

- Unit tests (language-appropriate framework)
- Integration tests
- E2E tests (Playwright for web)
- API contract tests

### Automation Examples

- "Generate tests for Python module `auth.py`"
- "Create Rust Axum endpoint tests"
- "Build Go API handler tests"
- "Generate TypeScript component tests"

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/test_generator.py`
- `/NeuroForge/neuroforge_backend/generators/test_templates/` (per-language)
- `/vibeforge/src/routes/automations/test-generator/+page.svelte`

---

## Milestone 5.3: Docs Generator (3 days)

### Tasks

1. Parse project structure
2. Generate API documentation
3. Update README
4. Generate architecture diagrams

### Generated Docs

- README.md (updated)
- SETUP.md
- ENVIRONMENT.md
- ARCHITECTURE.md
- ROUTES.md
- API.md
- CHANGELOG.md

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/docs_generator.py`
- `/vibeforge/src/routes/automations/docs-generator/+page.svelte`

---

## Milestone 5.4: CI/CD Generator (3 days)

**Reference:** `vibeforge_language_selector_blueprint.md` (Section 7)

### Tasks

1. Generate language-aware GitHub Actions YAML
2. Generate GitLab CI configurations
3. Generate multi-language Docker configs
4. Generate deployment scripts per language

### Language-Aware CI Features

**Python Projects:**

- pip/poetry dependency installation
- pytest execution
- Black/Flake8 linting

**TypeScript Projects:**

- pnpm/npm installation
- Vitest execution
- ESLint/Prettier

**Go Projects:**

- Go modules caching
- go test execution
- golint/gofmt

**Rust Projects:**

- Cargo caching
- cargo test execution
- clippy linting

**Multi-Language Projects:**

- Combined workflows
- Language-specific build stages
- Parallel test execution

### Generated CI Files

- `.github/workflows/test.yml` (language-aware)
- `.github/workflows/build.yml` (multi-stage if needed)
- `.github/workflows/deploy.yml`
- `Dockerfile` (multi-stage for multiple languages)
- `docker-compose.yml`
- `.dockerignore`
- Language-specific lint configs

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/ci_generator.py`
- `/NeuroForge/neuroforge_backend/generators/ci_templates/` (per-language)
- `/vibeforge/src/routes/automations/ci-generator/+page.svelte`

---

## Milestone 5.5: License & Governance Generator (2 days)

### Tasks

1. Generate LICENSE.md
2. Generate CONTRIBUTING.md
3. Generate SECURITY.md
4. Generate CODE_OF_CONDUCT.md

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/governance_generator.py`

---

## Milestone 5.6: Changelog Generator (2 days)

### Tasks

1. Parse git commits
2. Generate semantic changelog
3. Group by version
4. Add links to PRs/issues

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/changelog_generator.py`

---

## Milestone 5.7: Env Schema Automation (3 days)

### Tasks

1. Generate env.schema.json
2. Generate .env.example
3. Generate env.ts (frontend)
4. Generate settings.py (backend)
5. Generate ENVIRONMENT.md

### Generated Files

- `env.schema.json`
- `.env.example`
- `src/lib/env.ts`
- `app/settings.py`
- `ENVIRONMENT.md`

### Files to Create

- `/NeuroForge/neuroforge_backend/generators/env_generator.py`

---

## Milestone 5.8: Automation Dashboard (4 days)

### Tasks

1. Create automation hub page
2. Add automation history
3. Show usage analytics
4. Add favorites/templates

### UI Layout

- Grid of automation tools
- Recent automations
- Saved templates
- Usage stats

### Files to Create

- `/vibeforge/src/routes/automations/+page.svelte`
- `/vibeforge/src/lib/ui/automations/AutomationCard.svelte`
- `/vibeforge/src/lib/ui/automations/AutomationHistory.svelte`

---

# Cross-Cutting Concerns

## Database Schema Updates (DataForge)

### New Tables Needed

1. **stack_profiles** - Stack definitions
2. **project_templates** - User-created templates
3. **wizard_sessions** - In-progress wizards
4. **generated_projects** - Project metadata
5. **automation_history** - Automation execution logs
6. **icon_library** - Generated icons
7. **brand_assets** - Brand metadata

---

## API Integration Points

### VibeForge ↔ NeuroForge

- Stack Advisor recommendations
- SVG generation
- Code generation
- Test generation
- Docs generation

### VibeForge ↔ DataForge

- Stack profile storage/retrieval
- Project template management
- Context blocks for scaffolding
- Automation history
- Brand asset storage

### NeuroForge ↔ DataForge

- Context retrieval for generation
- Result storage
- Analytics logging

---

## Testing Strategy

### Phase 1

- Unit tests for stack profile models
- API tests for stack endpoints
- UI component tests

### Phase 2

- E2E tests for wizard flow
- Scaffolding generator tests
- Template rendering tests

### Phase 3

- Stack advisor prompt tests
- Recommendation accuracy tests
- Comparison logic tests

### Phase 4

- SVG validation tests
- Icon pack generation tests
- Image conversion tests

### Phase 5

- Generator output tests
- Template accuracy tests
- Integration tests for all generators

---

## Documentation Requirements

### Per Phase

1. **Phase 1:** Stack Profile documentation
2. **Phase 2:** Wizard user guide
3. **Phase 3:** Stack Advisor guide
4. **Phase 4:** Icon Lab user guide
5. **Phase 5:** Automation tools documentation

### Overall

- Architecture documentation
- API documentation
- User guides
- Video tutorials (optional)

---

## Risk Assessment

### High Risk Items

1. **SVG Generation Quality** - AI may generate invalid/poor SVGs
   - Mitigation: Add validation, fallback templates, manual edit option
2. **Scaffolding Complexity** - Generating full projects is complex
   - Mitigation: Start with simple templates, iterate

3. **Template Maintenance** - Keeping 7 stacks updated
   - Mitigation: Automated tests, community contributions

### Medium Risk Items

1. **Performance** - Large project generation may be slow
2. **Storage** - Generated projects/icons consume space
3. **LLM Costs** - Heavy AI usage may be expensive

---

## Success Metrics

### Phase 1

- ✅ 7 stack profiles defined and validated
- ✅ Stack API response time < 100ms
- ✅ All stack profiles have complete metadata

### Phase 2

- ✅ Wizard completion rate > 80%
- ✅ Generated projects compile successfully
- ✅ User satisfaction score > 4/5

### Phase 3

- ✅ Stack recommendation accuracy > 85%
- ✅ Advisor response time < 3s
- ✅ User accepts recommendations > 70%

### Phase 4

- ✅ Generated SVGs are valid
- ✅ Icon packs contain all required sizes
- ✅ Upload conversion success rate > 95%

### Phase 5

- ✅ Generated code passes linting
- ✅ Generated tests execute successfully
- ✅ Generated docs are accurate and complete

---

## Resource Requirements

### Team Size (Recommended)

- 2-3 Full-stack developers
- 1 Backend specialist (NeuroForge/Python)
- 1 Frontend specialist (SvelteKit)
- 1 DevOps engineer (part-time)
- 1 Designer (part-time for Icon Lab)

### Infrastructure

- NeuroForge server (4-8 CPU, 16GB RAM)
- DataForge database (Postgres with pgvector)
- Redis cache
- File storage (S3 or local)
- CDN for generated assets (optional)

### External Services

- LLM APIs (OpenAI/Anthropic)
- Image processing (Sharp/ImageMagick)
- Vector generation (potrace/resvg)

---

## Budget Estimate

### Development Costs (16-20 weeks)

- Development team: 3 FTE × 20 weeks = 60 person-weeks
- At $1,500/week = **$90,000**

### Infrastructure (Monthly)

- Cloud hosting: $200-500/month
- LLM API costs: $100-500/month (varies with usage)
- Storage: $50-100/month
- **Total: $350-1,100/month**

### One-Time Costs

- Design assets: $2,000
- Initial testing: $5,000
- Documentation: $3,000
- **Total: $10,000**

**Grand Total:** ~$100,000 + $5,000-15,000/year ongoing

---

## Next Steps

### Immediate Actions (Week 1)

1. Review and approve this plan
2. Set up project tracking (Jira/Linear/GitHub Projects)
3. Assign team members to phases
4. Set up development environments
5. Create initial repository structure

### Week 2-3

- Begin Phase 1: Stack Profile System
- Set up CI/CD for testing
- Create project documentation structure
- Design initial UI mockups

### Week 4+

- Continue with planned phases
- Weekly sprint reviews
- Bi-weekly demos
- Monthly stakeholder updates

---

## Language Selector Integration Summary

**Reference Blueprint:** `vibeforge_language_selector_blueprint.md` (added Nov 22, 2025)

### What Was Added

The Language Selector feature has been integrated throughout the implementation plan:

1. **New Wizard Step (Step 2):** Language selection before stack selection
2. **15 Languages Supported:** JavaScript/TypeScript, Svelte, Solid, Python, Node.js, Go, Rust, Java, C, C++, Bash, SQL, Dart, Kotlin, Swift
3. **Language-Aware Scaffolding:** Templates adapt to selected languages
4. **Smart Stack Filtering:** Advisor recommends stacks based on language choices
5. **Multi-Language Automations:** Generators adapt to project languages
6. **DataForge Storage:** Project languages stored for cross-feature memory

### Impact on Timeline

- **Phase 1:** Added Milestone 1.4 (Language Data Models) - +2 days
- **Phase 2:** Added Milestone 2.3 (Language Selector) - +4 days, shifted subsequent steps
- **Phase 2:** Enhanced Milestone 2.9 (Scaffolding Engine) - language templates
- **Phase 3:** Enhanced Milestone 3.1 (Stack Advisor) - language filtering
- **Phase 5:** Enhanced all generator milestones - language-aware generation

**Total Added Time:** ~1 week across phases

### Key Files Added

- `/vibeforge/src/lib/data/languages.ts`
- `/vibeforge/src/lib/core/types/languages.ts`
- `/vibeforge/src/lib/ui/wizard/LanguageSelector.svelte`
- `/vibeforge/src/lib/ui/wizard/LanguageChip.svelte`
- `/vibeforge/src/lib/ui/wizard/LanguageEffectsPanel.svelte`
- `/DataForge/app/models/project_languages.py`
- `/DataForge/app/routers/project_languages.py`
- `/NeuroForge/neuroforge_backend/models/language_models.py`
- `/NeuroForge/neuroforge_backend/agents/language_stack_filter.py`
- `/NeuroForge/neuroforge_backend/scaffolding/language_templates/`
- `/NeuroForge/neuroforge_backend/generators/language_templates.py`
- `/NeuroForge/neuroforge_backend/generators/test_templates/`
- `/NeuroForge/neuroforge_backend/generators/ci_templates/`

### Benefits

- **Smarter Recommendations:** Stack suggestions match selected languages
- **Better Scaffolding:** Generated code uses correct languages and patterns
- **Proper Testing:** Tests generated in appropriate frameworks
- **Correct CI/CD:** Build pipelines match project languages
- **Future-Proof:** Foundation for language policy enforcement (Pro/Enterprise)

---

## Conclusion

This implementation plan provides a clear roadmap from the current system state to a fully automated, language-aware project creation and development workflow system. The phased approach allows for:

- **Incremental delivery** of value
- **Risk mitigation** through early testing
- **Flexibility** to adjust based on feedback
- **Clear milestones** for tracking progress
- **Language awareness** throughout the entire automation pipeline

The blueprint is ambitious but achievable with proper planning, resources, and execution. Each phase builds logically on the previous one, creating a cohesive and powerful automation platform for the Forge ecosystem. The addition of the Language Selector feature makes VibeForge a true multi-language AI coding environment.

---

**Plan Status:** ✅ Ready for Review  
**Next Action:** Schedule kickoff meeting and assign Phase 1 tasks
