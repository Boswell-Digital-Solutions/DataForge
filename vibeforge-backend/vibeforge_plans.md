# VibeForge – Phased Implementation Roadmap (Forge-Native)

## Ecosystem Assumptions

- **VibeForge** = Prompt Engineering Workbench (SvelteKit frontend)  
- **NeuroForge** = LLM Orchestration, model routing, executions, deployment engine  
- **DataForge** = Knowledge base, context storage, analytics, metrics, logs  

> All new backend capabilities should be implemented as **modules/APIs in NeuroForge/DataForge**, not as a separate greenfield backend.

---

## Phase 0 – Foundation (Weeks 1–2)

**Goal:** Stand up the core VibeForge workbench UI on top of existing Forge backend

### Week 1 – Project + Layout Setup

#### VibeForge (Frontend – SvelteKit)

**Initialize / solidify project:**

- SvelteKit + TypeScript  
- Tailwind v4 with Forge design tokens  
- `motion-svelte` (or Svelte transitions) for micro-interactions  
- Monaco editor integration for the prompt editing surface  

**Implement base layout:**

- **Top bar:** product branding (VibeForge logo, Forge ecosystem switcher, user menu)  
- **Left rail:** navigation + prompt list + context/library entry points  
- **Main canvas:** 3-column layout  
  - Column 1: Context (DataForge-powered later)  
  - Column 2: Prompt Editor (Monaco)  
  - Column 3: Outputs / Execution results  

**Hook up auth:**

- Integrate with existing Forge auth (e.g., Clerk or existing JWT/OpenID) so VibeForge uses the same user/tenant identity as NeuroForge & DataForge.

#### NeuroForge (Backend – LLM Engine)

No new heavy infra; just:

- Confirm existing execution endpoint contract, e.g.:
  - `POST /api/v1/prompts/execute` or `POST /api/v1/llm/execute`
- Ensure endpoint:
  - **Accepts:** model, prompt text, optional context IDs, metadata.  
  - **Returns:** output, tokens in/out, cost, latency, model name.  
- Add a lightweight **“PromptWorkbench”** API namespace (even if stubbed):
  - `POST /api/v1/workbench/prompts` (create stub prompt record)  
  - `GET /api/v1/workbench/prompts/{id}` (fetch prompt content + metadata)

#### DataForge (Backend – Knowledge + Analytics)

No major changes yet. Just:

- Reserve tables / schemas for:
  - `prompts` (owned by NF but stored in shared DB if that’s your pattern)  
  - `prompt_executions` (metrics logging)
- Make sure DataForge is ready to accept:
  - Execution logs + metrics from NeuroForge (even if not fully wired yet).

---

### Week 2 – Core Data Models + First Execution

#### VibeForge (Frontend)

**Implement Prompt Editor flow:**

- **Create:** “New Prompt” button → calls NF to create prompt record.  
- **Load:** fetch prompt content + metadata from NF.  
- **Edit:** Monaco editor bound to the prompt’s content (local state only for now).  
- **Execute:** “Run” button that:
  - Sends current content + selected model to NeuroForge execute endpoint.  
  - Displays result in the right column (plain text view initially).  

**Basic UX:**

- Simple prompt list in the left rail.  
- Basic status toasts (executing / success / error).

#### NeuroForge (Backend)

**Define core tables/entities** (in NF DB or shared Forge DB):

- `prompts(id, owner_id, name, description, latest_version_id, created_at, updated_at, …)`  
- `prompt_executions(id, prompt_id, user_id, model, input_tokens, output_tokens, cost_usd, latency_ms, status, created_at, …)`

**Implement basic endpoints:**

- `POST /api/v1/workbench/prompts` – create  
- `GET /api/v1/workbench/prompts/{id}` – read  
- `GET /api/v1/workbench/prompts` – list for current user  
- `POST /api/v1/workbench/prompts/{id}/execute` – wraps existing NF LLM orchestration logic  

**Wire execution logging:**

- Every call from VibeForge writes a `prompt_executions` row.

#### DataForge (Backend)

Optional but recommended:

- Create views / materialized views for later analytics:
  - `prompt_execution_stats` – aggregated cost, success rate, usage by prompt & model.

#### MVP Demo (End of Phase 0)

- User logs in via Forge auth  
- Creates a prompt in VibeForge  
- Edits it in the Monaco editor  
- Executes it via NeuroForge  
- Sees output + minimal metadata  

---

## Phase 1 – Quick Wins (Weeks 3–6)

**Goal:** Ship visible power features: versioning, cost awareness, shortcuts, context

### Week 3 – Version Control & Auto-Save

#### VibeForge (Frontend)

**Add auto-save with debounce:**

- When user stops typing for ~2 seconds → `POST` new version to NF.

**UI:**

- Version timeline / dropdown for each prompt.  
- “Restore version” button.  
- Diff modal / diff pane using Monaco’s diff editor.

#### NeuroForge (Backend)

**Data:**

- `prompt_versions(id, prompt_id, content, parent_version_id, created_at, created_by, auto_saved bool, …)`  
- Add `current_version_id` to `prompts`.

**Endpoints:**

- `POST /api/v1/workbench/prompts/{id}/versions` – create version  
- `GET /api/v1/workbench/prompts/{id}/versions` – list  
- `POST /api/v1/workbench/prompts/{id}/versions/{version_id}/restore` – set as current  

**Business logic:**

- Auto-save vs manual save flagged separately.  
- Rollback simply updates `current_version_id`.

#### DataForge (Backend)

Optional:

- Index `prompt_versions` for analytics (e.g., number of edits before stable version).

---

### Week 4 – Cost & Performance Visibility

#### VibeForge (Frontend)

- Add **real-time token and cost estimators** in the prompt header:
  - Uses NF’s `estimate` endpoint (no real LLM call, just tokenizer + pricing).
- Show execution history:
  - Side panel or right-column tab:
    - Recent runs with timestamp, model, cost, latency, status.
- Add simple **success-rate chart** using your chosen Svelte chart library.

#### NeuroForge (Backend)

**Add token & cost utilities:**

- `POST /api/v1/workbench/prompts/{id}/estimate`:
  - **Inputs:** prompt content, selected models, context IDs.  
  - **Outputs:** token counts + estimated cost per run.

**Extend** `prompt_executions` to track:

- error codes  
- truncated flags  
- user-provided labels  

**Provide summary endpoints:**

- `GET /api/v1/workbench/prompts/{id}/executions` – list/paginated  
- `GET /api/v1/workbench/prompts/{id}/summary` – pre-aggregated stats (success rate, avg cost, avg latency).

#### DataForge (Backend)

Store / aggregate execution metrics:

- Materialized views or TimescaleDB integration for:
  - success rate over time  
  - cost by model  
  - latency distributions  

---

### Week 5 – Keyboard Shortcuts & Command Palette

#### VibeForge (Frontend)

**Implement global keyboard shortcuts:**

- `mod+Enter` → execute current prompt  
- `mod+s` → manual save snapshot/version  
- `mod+d` → duplicate prompt  
- `mod+k` → open command palette  
- `mod+/` → open shortcuts cheat sheet  

**Command palette:**

Quick actions:

- Switch prompt  
- Execute prompt  
- Open analytics  
- Open context manager  

#### NeuroForge / DataForge (Backend)

No major changes; just ensure:

- APIs are idempotent and fast enough to be called frequently via shortcuts.

---

### Week 6 – Context Management (DataForge Integration)

#### VibeForge (Frontend)

**Implement Context Manager in the left column:**

- List all context blocks (from DataForge) attached to the current prompt.  
- Add / remove / reorder contexts.  
- Show per-context metrics:
  - usage rate  
  - cost contribution  
  - quality impact (when available later from NF analytics).  

**UX:**

- Drag-and-drop ordering.  
- Toggle “include/exclude” per context for an execution.

#### NeuroForge (Backend)

**Execution modeling:**

- Ensure execute/estimate endpoints accept:
  - `context_ids: [string]`
- Log context usage in `prompt_executions`:
  - store context IDs used per run.

#### DataForge (Backend)

**Context as first-class objects:**

- `contexts(id, owner_id, team_id, title, content, embedding_id, …)`  
- `prompt_context_links(prompt_id, context_id, order, created_at)`

**Analytics (per-context):**

- how often used  
- effect on success rate / cost / tokens  

#### Milestone 1 Demo

Full prompt editor with:

- Version history  
- Cost estimation  
- Execution history  
- Keyboard shortcuts  
- Context management powered by DataForge  

---

## Phase 2 – Intelligence (Weeks 7–12)

**Goal:** Add NeuroForge-powered AI assistance for prompt quality & testing

### Weeks 7–8 – Smart Prompt Suggestions

#### VibeForge (Frontend)

**Inline suggestions:**

- Editor decorations for:
  - contradictions  
  - ambiguities  
  - missing guardrails  
  - optimization suggestions  
- Side panel listing issues, with “apply fix” button per item.

**Real-time UX:**

- When user clicks **“Analyze Prompt”**:
  - Show “Analyzing…” state.  
  - Receive WebSocket event when suggestions ready.

#### NeuroForge (Backend)

**Background analysis pipeline:**

- Endpoint: `POST /api/v1/workbench/prompts/{id}/analyze`
  - Enqueues analysis job.

**Worker:**

- Calls NF’s model routing (Claude / others) to run analysis prompt.  
- Parses structured JSON:
  - `contradictions`  
  - `ambiguities`  
  - `optimizations`  
  - `missing_guardrails`  
- Writes to `prompt_suggestions` table.

**WebSocket / SSE:**

- Emit `suggestions_ready` event to the user.

**Data:**

- `prompt_suggestions(prompt_id, data_json, updated_at, model_used, …)`

#### DataForge (Backend)

Optional:

- Store analysis history for longitudinal quality metrics.

---

### Weeks 9–10 – Test Generation & Execution

#### VibeForge (Frontend)

**Test Suite UI:**

- “Generate test suite” button for a prompt.  
- Table of test cases:
  - category (happy path, edge case, boundary, failure mode)  
  - input  
  - expected behavior/output  
  - last result (pass/fail)  
- “Run all tests” button + progress view.

#### NeuroForge (Backend)

**Test suite APIs:**

- `POST /api/v1/workbench/prompts/{id}/tests/auto-generate`
  - Uses NF models to generate JSON test cases.
- `POST /api/v1/workbench/test-suites/{suite_id}/run`
  - Executes all tests through NF’s execution engine.
- `GET /api/v1/workbench/test-suites/{suite_id}/results`

**Data:**

- `test_suites(id, prompt_id, name, created_at, created_by, …)`  
- `test_cases(id, test_suite_id, input_data, expected_behavior, expected_output, category, …)`  
- `test_results(id, test_case_id, execution_id, passed, actual_output, created_at, …)`

#### DataForge (Backend)

Persist & index test results:

- Enable dashboards later:
  - pass rate over time  
  - flaky test detection  
  - failure clustering  

---

### Weeks 11–12 – Model Comparison

#### VibeForge (Frontend)

**Model comparison view:**

- Grid showing per model:
  - output text  
  - tokens in/out  
  - cost  
  - latency  
  - success/quality metrics (if available).  

**UX:**

- Input area where user provides one test input.  
- “Compare models” button triggers simultaneous runs.

#### NeuroForge (Backend)

**Multi-model execution API:**

- `POST /api/v1/workbench/prompts/{id}/compare-models`
  - Executes same logical prompt across several models in parallel.
  - Returns combined result payload (per model).

**Optional:**

- Basic quality heuristics:
  - e.g., content length, refusal detection, hallucination markers.  
- Model recommendation signal.

#### DataForge (Backend)

Store comparison runs:

- Use for later analytics:
  - cost vs quality tradeoffs  
  - per-model performance tracking  

#### Milestone 2 Demo

AI-assisted prompt quality:

- Smart suggestions  
- Auto-generated test suites  
- Multi-model comparison  

---

## Phase 3 – Production (Weeks 13–18)

**Goal:** Turn prompts into deployable APIs & MCP servers with monitoring

### Weeks 13–14 – One-Click API Deployment

#### VibeForge (Frontend)

- “Deploy as API” button in prompt view:
  - Choose environment: dev / staging / prod.  
- After deployment:
  - Show endpoint URL.  
  - Show auto-generated TypeScript & Python SDK code snippets.

#### NeuroForge (Backend)

**Deployment engine:**

- `POST /api/v1/workbench/prompts/{id}/deploy/api`
  - Generates function code (Lambda, Vercel, etc.) based on prompt template.

**Deployment integration:**

- AWS Lambda, Vercel Functions, or your chosen platform.

**Store deployment metadata in `deployments` table:**

- `deployments(id, prompt_id, type(api/mcp/…), env, endpoint_url, deployed_at, status, …)`

**SDK generation:**

- Functions to generate:
  - TypeScript client  
  - Python client  
- Return these as strings to VibeForge.

#### DataForge (Backend)

Track deployments:

- Enable linking deployments to usage & metrics later.

---

### Weeks 15–16 – MCP Server Generation (NeuroForge as MCP Factory)

#### VibeForge (Frontend)

**“Generate MCP Server” action:**

- User selects:
  - package name  
  - description  
- UI shows:
  - npm package name  
  - install command  
  - Claude config snippet  

#### NeuroForge (Backend)

**MCP server scaffolding:**

- `POST /api/v1/workbench/prompts/{id}/deploy/mcp`
  - Generates MCP server code from prompt template.
  - Builds Node workspace (`index.ts`, `package.json`, `tsconfig`).
  - Runs:
    - `npm install`  
    - `npm run build`  
    - `npm publish`  
  - Stores `package_name` in `deployments`.

**Provides:**

- Install command, e.g. `npm install -g mcp-<prompt-name>`.  
- Minimal Claude configuration JSON for user.

#### DataForge (Backend)

- Track which MCP packages belong to which prompts / teams.

---

### Weeks 17–18 – Production Monitoring & Alerts

#### VibeForge (Frontend)

**Monitoring tab per deployment:**

- Charts:
  - success rate over time  
  - cost over time  
  - latency (P50/P95)  
- List of alerts (with severity and timestamps).  
- “Rollback deployment” button (if NF supports automatic rollback).

#### NeuroForge (Backend)

**Metrics middleware:**

- Wraps deployed endpoints to log:
  - `deployment_id`  
  - status code  
  - cost  
  - latency  

**Alert rules:**

- Configurable thresholds per deployment:
  - min success rate  
  - max latency  
  - cost ceilings  
- `check_alerts()` function:
  - triggers Slack/email alerts  
  - may flag deployment for rollback.

#### DataForge (Backend)

**Time-series metrics storage:**

- `api_metrics(time, deployment_id, request_count, error_count, avg_latency_ms, total_cost_usd, success_rate, …)`
- Queries for rolling windows (last hour / day / week).

#### Milestone 3 Demo

- Prompt → API / MCP deployment → monitored and alertable, all driven from VibeForge.

---

## Phase 4 – Collaboration (Weeks 19–24)

**Goal:** Turn VibeForge into a team workbench: real-time editing, reviews, integrations

### Weeks 19–20 – Real-Time Collaborative Editing

#### VibeForge (Frontend)

**Collaborative editor:**

- Yjs + y-websocket bound to Monaco.  
- Show:
  - remote cursors with user colors  
  - active users list  

**Auto-save:**

- Yjs doc changes are periodically synced back to NF as new versions.

#### NeuroForge (Backend)

**Option A:**

- Run a separate collaboration service (Node/WS) but keep it under NeuroForge “infrastructure”.

**Option B:**

- Integrate WS server directly into NF (if using ASGI + websockets).

Still rely on NF:

- to persist prompt content and versions.

#### DataForge (Backend)

Optional:

- Store collaboration metrics:
  - number of collaborators  
  - edit frequency  
  - “hot” prompts for teams  

---

### Weeks 21–22 – Team Patterns & Review Workflow

#### VibeForge (Frontend)

**Team workspace screens:**

- Left nav: switch workspace/team.  
- **“Patterns” library:**
  - cards with title, description, content snippet, upvotes  
  - fork button → creates a forked prompt in VibeForge  

**Prompt review flow:**

- Diff view between versions.  
- Comment threads anchored to lines.  
- Approve / Request changes buttons.

#### NeuroForge (Backend)

**Data:**

- `teams`, `team_members`  
- `patterns(id, team_id, title, description, content, upvotes, created_at, …)`  
- `prompt_reviews(id, prompt_id, reviewer_id, status, comments_json, created_at, …)`

**Endpoints:**

- CRUD for patterns.  
- `POST /api/v1/workbench/prompts/{id}/reviews` – submit review.  
- `GET /api/v1/workbench/prompts/{id}/reviews` – history.

#### DataForge (Backend)

- Store patterns in DF if you treat them as reusable knowledge artifacts:
  - indexing & semantic search for “prompt patterns”.

---

### Weeks 23–24 – Integrations (Slack, GitHub, Zapier, etc.)

#### VibeForge (Frontend)

**Integrations settings page:**

- Connect Slack workspace.  
- Connect GitHub org/repo.  
- Configure simple automations (e.g., PR summary prompt, Slack run command).

#### NeuroForge (Backend)

**Slack integration:**

- Slash commands (e.g. `/vibeforge run <prompt-name> <input>`).  
- Uses NF execution engine to run prompts.

**GitHub integration:**

- Webhook endpoint to:
  - auto-generate PR summaries using a designated prompt.

**Zapier:**

- Expose NF endpoints that can trigger VibeForge prompts from Zapier.

#### DataForge (Backend)

**Store integration settings:**

- Which team → which Slack workspace / GitHub repos / Zapier hooks.

#### Milestone 4 Demo

- Teams collaborate in real time, review prompts, and wire VibeForge into Slack/GitHub.

---

## Phase 5 – Advanced Features (Weeks 25–30)

**Goal:** Power-user capabilities: batch runs, deep analytics, optimization tools

### Weeks 25–26 – Batch Processing

#### VibeForge (Frontend)

**Batch execution screen:**

- CSV upload (map columns to prompt variables).  
- Show:
  - estimated cost  
  - job status  
  - ability to download results  

#### NeuroForge (Backend)

**Batch API:**

- `POST /api/v1/workbench/prompts/{id}/batch`
  - parses CSV  
  - queues chunks onto NF’s queue system  
  - returns job ID + estimated cost  
- `GET /api/v1/workbench/batch/{job_id}/results`

**Workers:**

- Run each row as a separate NF execution.  
- Store results and progress in Redis/DB.

#### DataForge (Backend)

Persist batch results for later analytics:

- cost per batch  
- error rows  
- per-customer/per-tenant reporting  

---

### Weeks 27–28 – Advanced Analytics

#### VibeForge (Frontend)

**Analytics dashboard per prompt:**

- Success rate trend chart.  
- Cost analysis (per model, per timeframe).  
- Token efficiency metrics.  
- Model performance table.

#### NeuroForge (Backend)

**Aggregation logic:**

- Summarize metrics from `prompt_executions` and `api_metrics`.  
- `GET /api/v1/workbench/prompts/{id}/analytics`:
  - `successRate[]`  
  - `costByModel[]`  
  - `avgTokens`  
  - `efficiencyScore`  
  - `modelComparison` table  

#### DataForge (Backend)

Heavy lifting for analytics:

- Views / ETL for:
  - cost rollups  
  - model performance heatmaps  
  - token efficiency scoring  

---

### Weeks 29–30 – Optimization Tools (Few-shot, Temperature, Adversarial)

#### VibeForge (Frontend)

**Optimization panel:**

- “Optimize examples” button.  
- UI comparison:
  - original vs optimized examples  
  - metrics: quality score, tokens, cost  
- One-click “Apply optimized version”.

#### NeuroForge (Backend)

**Optimization endpoints:**

- `POST /api/v1/workbench/prompts/{id}/optimize-examples`
  - Uses NF’s models to:
    - prune redundant examples  
    - improve diversity  
    - propose new examples  
  - Runs small A/B tests to compare original vs optimized.
- `POST /api/v1/workbench/prompts/{id}/adversarial-tests`
  - Generates challenging inputs to probe prompt robustness.

**Data:**

- store experiment runs & their outcomes.

#### DataForge (Backend)

Track optimization experiments:

- `prompt_optimization_runs` with:
  - original quality  
  - new quality  
  - token delta  
  - cost savings  

#### Milestone 5 Demo

- A full optimization suite that helps users compress, harden, and improve prompts over time.
