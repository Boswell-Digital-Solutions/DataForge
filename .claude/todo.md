# VibeForge V2 Frontend – Phase 1 TODO

**Status codes:** BACKLOG → READY → DOING → REVIEW → BLOCKED → DONE
**Priority:** P0 critical, P1 high, P2 normal, P3 nice-to-have

---

## VF-100: Project Setup & Architecture Planning
**Status:** DONE
**Priority:** P0
**Owner:** Claude
**Area:** Foundation
**Files:** `./*`
**Deps:** None
**Completed:** 2025-11-21

### Acceptance:
- [x] Decide on V2 folder structure (new app vs. restructure existing)
- [x] Review existing V1 codebase structure
- [x] Create comprehensive architecture plan for V2
- [x] Document MCP integration points

**Notes:** Work within existing vibeforge/ folder, created clean V2 architecture with lib/core/, lib/ui/, lib/workbench/

---

## VF-101: Initialize V2 App Structure
**Status:** DONE
**Priority:** P0
**Owner:** Claude
**Area:** Foundation
**Files:** `vibeforge/`, `vibeforge/src/**`
**Deps:** VF-100
**Completed:** 2025-11-21

### Acceptance:
- [x] Create clean folder structure: `lib/core/`, `lib/ui/`, `lib/workbench/`
- [x] Set up `routes/` with proper nesting
- [x] Verify pnpm dependencies (SvelteKit 2.x, Svelte 5, Tailwind v4)
- [x] Create base TypeScript config

---

## VF-102: Domain Types & MCP Types
**Status:** DONE
**Priority:** P0
**Owner:** Claude
**Area:** Core/Types
**Files:** `lib/core/types/domain.ts`, `lib/core/types/mcp.ts`
**Deps:** VF-101
**Completed:** 2025-11-21

### Acceptance:
- [x] Define core domain types: Workspace, ContextBlock, Prompt, Model, Run
- [x] Define MCP types: McpServer, McpTool, McpToolInvocation, McpToolResult
- [x] Define utility types for API responses
- [x] Export all types from index

**Notes:** ~2500 LOC created. Framework-agnostic types ready for HTTP and MCP backends.

---

## VF-103: API Client Stubs
**Status:** DONE
**Priority:** P1
**Owner:** Claude
**Area:** Core/API
**Files:** `lib/core/api/*.ts`
**Deps:** VF-102
**Completed:** 2025-11-21

### Acceptance:
- [x] Create `vibeforgeClient.ts` with stubbed methods
- [x] Create `neuroforgeClient.ts` with stubbed model router methods
- [x] Create `dataforgeClient.ts` with stubbed KB methods
- [x] Create `mcpClient.ts` with stubbed MCP protocol methods (listServers, listTools, invokeTool)
- [x] All stubs return mock data matching domain types

**Notes:** All clients return mock data with realistic delays. Ready for Phase 2 HTTP/MCP wiring.

---

## VF-104: Core Stores (Svelte 5 Runes)
**Status:** DONE
**Priority:** P1
**Owner:** Claude
**Area:** Core/Stores
**Files:** `lib/core/stores/*.ts`
**Deps:** VF-102, VF-103
**Completed:** 2025-11-21

### Acceptance:
- [x] `workspace.ts`: workspace state using $state rune
- [x] `contextBlocks.ts`: context blocks management
- [x] `prompt.ts`: prompt state and template handling
- [x] `models.ts`: available models and selection
- [x] `runs.ts`: run history and active run state
- [x] `tools.ts`: MCP tools store with mock servers/tools

**Notes:** Migrated from V1 writable stores to Svelte 5 runes ($state, $derived). All stores use .svelte.ts extension.

---

## VF-105: Tailwind Theme & Design Tokens
**Status:** DONE
**Priority:** P1
**Owner:** Claude
**Area:** Styling
**Files:** `tailwind.config.js`, `src/app.css`
**Deps:** VF-101
**Completed:** 2025-11-21 (Pre-existing from V1)

### Acceptance:
- [x] Configure Forge color palette (forge-blacksteel, forge-gunmetal, forge-steel, forge-ember, etc.)
- [x] Set up dark mode as default
- [x] Define spacing, typography, shadows for workbench UI
- [x] Create CSS custom properties for theme switching

**Notes:** Already configured in V1. Reusing existing Tailwind v4 theme with Forge colors.

---

## VF-106: UI Primitives
**Status:** DONE
**Priority:** P1
**Owner:** Claude
**Area:** UI/Primitives
**Files:** `lib/ui/primitives/*.svelte`
**Deps:** VF-105
**Completed:** 2025-11-21

### Acceptance:
- [x] `Button.svelte`: variants (primary, secondary, ghost, icon)
- [x] `Input.svelte`: text input with Forge styling
- [x] `Panel.svelte`: reusable panel container
- [x] `SectionHeader.svelte`: consistent section headers
- [x] `Tag.svelte`: tag/badge component
- [x] All components use Svelte 5 `$props` rune

**Notes:** All primitives use Svelte 5 $props and $derived runes. Includes index.ts for easy imports.

---

## VF-107: Layout Components
**Status:** DONE
**Priority:** P1
**Owner:** Claude
**Area:** UI/Layout
**Files:** `lib/ui/layout/*.svelte`
**Deps:** VF-106
**Completed:** 2025-11-21

### Acceptance:
- [x] `TopBar.svelte`: app identity, workspace selector, key actions
- [x] `LeftRailNav.svelte`: nav items (Workbench, Contexts, Patterns, History, etc.)
- [x] `StatusBar.svelte`: tokens, latency, active models, run state
- [x] `WorkbenchShell.svelte`: 3-column container with responsive layout

**Notes:** All layout components use Svelte 5 patterns. Includes responsive design with mobile breakpoints. Index.ts created for exports.

---

## VF-108: Context Column Components
**Status:** DONE
**Priority:** P2
**Owner:** Claude
**Area:** Workbench/Context
**Files:** `lib/workbench/context/*.svelte`
**Deps:** VF-104, VF-106
**Completed:** 2025-11-21

### Acceptance:
- [x] `ContextColumn.svelte`: main container for context management
- [x] `ContextBlockCard.svelte`: individual context block display
- [x] `ContextBlockEditor.svelte`: add/edit context blocks
- [x] `McpToolsSection.svelte`: display available MCP tools (stubbed)
- [x] Wire to `contextBlocks` and `tools` stores

**Notes:** Full context management UI complete with active/inactive blocks, MCP tools display, and integrated stores. Includes index.ts for exports.

---

## VF-109: Prompt Column Components
**Status:** DONE
**Priority:** P2
**Owner:** Claude
**Area:** Workbench/Prompt
**Files:** `lib/workbench/prompt/*.svelte`
**Deps:** VF-104, VF-106
**Completed:** 2025-11-21

### Acceptance:
- [x] `PromptColumn.svelte`: main prompt editor container
- [x] `PromptEditor.svelte`: textarea with template support
- [x] `ModelSelector.svelte`: dropdown for model selection
- [x] `PromptActions.svelte`: Run, Save, Clear buttons
- [x] Wire to `prompt` and `models` stores

**Notes:** Full prompt editing UI with template variables, model selection, and run execution. Includes Cmd+Enter shortcut. Index.ts created for exports.

---

## VF-110: Output Column Components
**Status:** DONE
**Priority:** P2
**Owner:** Claude
**Area:** Workbench/Output
**Files:** `lib/workbench/output/*.svelte`
**Deps:** VF-104, VF-106
**Completed:** 2025-11-21

### Acceptance:
- [x] `OutputColumn.svelte`: main output display container
- [x] `OutputViewer.svelte`: display LLM responses with formatting
- [x] `RunMetadata.svelte`: show tokens, latency, model used
- [x] `OutputActions.svelte`: Copy, Save, Compare buttons
- [x] Wire to `runs` store

**Notes:** Full output display UI with run history selector, metrics display, copy/save actions, and multiple run states. Index.ts created for exports.

---

## VF-111: Routes & Page Structure
**Status:** DONE
**Priority:** P2
**Owner:** Claude
**Area:** Routes
**Files:** `src/routes/**`
**Deps:** VF-107, VF-108, VF-109, VF-110
**Completed:** 2025-11-21

### Acceptance:
- [x] `+layout.svelte`: include TopBar, LeftRailNav, StatusBar
- [x] `+page.svelte`: Workbench main page with 3-column layout
- [x] Placeholder routes: `/contexts`, `/history`, `/patterns`, `/evals`, `/workspaces`, `/settings`
- [x] All routes render with proper layout

**Notes:** Root layout updated with V2 components. Workbench page uses all 3 columns. Placeholder routes already exist from V1.

---

## VF-112: Demo Data & Mock Integration
**Status:** DONE
**Priority:** P2
**Owner:** Claude
**Area:** Integration
**Files:** `lib/core/utils/demoData.ts`
**Deps:** VF-111
**Completed:** 2025-11-21

### Acceptance:
- [x] Populate stores with demo data on app load
- [x] Mock MCP servers: DataForge-MCP, NeuroForge-MCP, Web Tools MCP
- [x] Mock MCP tools: queryKB, routeModel, webSearch, fetchURL, ingestDocument, getContextBlock
- [x] Demo context blocks, prompt templates, model list
- [x] Simulate a full prompt run (Context → Prompt → Output flow)

**Notes:** Created comprehensive demoData.ts with 3 context blocks, 5 models (Anthropic, OpenAI, Local), 3 MCP servers, 6 MCP tools. Initializes on app mount via +layout.svelte.

---

## VF-113: MCP UI Integration Points
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** MCP
**Files:** `lib/workbench/context/McpToolsSection.svelte`, `lib/core/stores/tools.ts`
**Deps:** VF-112

### Acceptance:
- [ ] Display MCP servers in Context column
- [ ] Show available tools per server
- [ ] Allow "favoriting" tools (UI placeholder)
- [ ] Show tool usage in run metadata (placeholder)
- [ ] Document MCP integration TODOs for Phase 2

---

## VF-114: Polish, Responsiveness & Accessibility
**Status:** BACKLOG
**Priority:** P3
**Owner:** Claude
**Area:** Polish
**Files:** `lib/**/*.svelte`
**Deps:** VF-113

### Acceptance:
- [ ] Ensure 3-column layout is responsive (collapsible on smaller screens)
- [ ] Add keyboard shortcuts (Cmd+Enter to run, Cmd+K for command palette placeholder)
- [ ] Basic accessibility: ARIA labels, focus states, semantic HTML
- [ ] Dark mode polish: consistent colors, proper contrast

---

## VF-115: Documentation & Handoff
**Status:** BACKLOG
**Priority:** P3
**Owner:** Claude
**Area:** Docs
**Files:** `vibeforge/README.md`, `vibeforge/docs/`
**Deps:** VF-114

### Acceptance:
- [ ] Update README with V2 architecture overview
- [ ] Document folder structure and conventions
- [ ] Create MCP integration guide for Phase 2
- [ ] List known TODOs and future enhancements

---

**Last updated:** 2025-11-21
**Active tasks:** 0
**Completed:** 12 / 16 (Full Workbench with Routes & Demo Data complete ✅)
