# VibeForge Frontend-Backend Integration Guide

Complete end-to-end integration path between SvelteKit frontend (VibeForge) and FastAPI + Rust backend (Forge).

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [API Client (TypeScript)](#api-client-typescript)
3. [Integration Points](#integration-points)
4. [Example Request/Response](#example-requestresponse)
5. [Running Both Servers](#running-both-servers)
6. [End-to-End Testing](#end-to-end-testing)
7. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Backend (.env)

Create `.env` file in `vibeforge-backend/`:

```dotenv
# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=true

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# CORS - Allow frontend
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# Logging
LOG_LEVEL=INFO
```

### Frontend (.env.local)

Create `.env.local` in `vibeforge/` (SvelteKit root):

```env
# Backend API
PUBLIC_API_BASE_URL=http://localhost:8000
PUBLIC_API_VERSION=v1

# Optional: Feature flags
PUBLIC_ENABLE_LOCAL_LLM=false
```

**Important**:

- Backend variables go in backend `.env` (server-side only)
- Frontend variables go in frontend `.env.local` (prefixed with `PUBLIC_` if needed client-side)
- Frontend cannot access backend secrets directly (Anthropic/OpenAI keys stay on backend)

---

## API Client (TypeScript)

### File: `src/lib/api/client.ts`

````typescript
/**
 * VibeForge API Client
 *
 * Provides type-safe HTTP methods for communicating with the FastAPI backend.
 * Handles token counting, run creation, and history retrieval.
 */

import type {
  ModelRun,
  CreateRunRequest,
  RunHistory,
  ContextBlock,
} from "./types";

// Get API base URL from environment
const API_BASE_URL =
  import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_VERSION = import.meta.env.PUBLIC_API_VERSION || "v1";

const VIBEFORGE_BASE = `${API_BASE_URL}/${API_VERSION}/vibeforge`;

/**
 * API error with proper typing
 */
export class APIError extends Error {
  constructor(public status: number, public details: string) {
    super(`API Error ${status}: ${details}`);
    this.name = "APIError";
  }
}

/**
 * Request configuration with sensible defaults
 */
function createFetchOptions(method: string = "GET"): RequestInit {
  return {
    method,
    headers: {
      "Content-Type": "application/json",
      // CORS is pre-flighted automatically by browser
    },
    // Don't send credentials unless explicitly needed
    credentials: "omit",
  };
}

/**
 * Parse response and handle errors
 */
async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type");
  let body: any;

  try {
    if (contentType?.includes("application/json")) {
      body = await response.json();
    } else {
      body = await response.text();
    }
  } catch (e) {
    body = null;
  }

  if (!response.ok) {
    const detail = body?.detail || body?.message || "Unknown error";
    throw new APIError(response.status, detail);
  }

  return body as T;
}

/**
 * Health check endpoint
 *
 * @returns Status of the VibeForge service
 */
export async function healthCheck(): Promise<{
  status: string;
  service: string;
}> {
  const response = await fetch(
    `${VIBEFORGE_BASE}/health`,
    createFetchOptions()
  );
  return handleResponse(response);
}

/**
 * Create and execute a new model run
 *
 * This is the main entry point for sending prompts to the LLM.
 *
 * @param request - Run configuration with model, prompt, and contexts
 * @returns The executed run with output and token counts
 * @throws APIError if the request fails
 *
 * @example
 * ```typescript
 * const run = await postRun({
 *   model: 'claude-3-opus-20240229',
 *   prompt: 'Analyze this code',
 *   active_contexts: [
 *     {
 *       id: 'ctx-1',
 *       title: 'Guidelines',
 *       content: 'Use TypeScript...',
 *       kind: 'code',
 *       priority: 1,
 *     }
 *   ],
 * });
 *
 * console.log(`Output: ${run.output}`);
 * console.log(`Tokens: ${run.tokens_used?.total_tokens}`);
 * ```
 */
export async function postRun(request: CreateRunRequest): Promise<ModelRun> {
  const response = await fetch(`${VIBEFORGE_BASE}/run`, {
    ...createFetchOptions("POST"),
    body: JSON.stringify(request),
  });
  return handleResponse<ModelRun>(response);
}

/**
 * Retrieve a specific run by ID
 *
 * Use this to check the status of a run or fetch historical data.
 *
 * @param runId - The ID of the run to retrieve
 * @returns The run with all metadata
 * @throws APIError if the run is not found
 */
export async function getRun(runId: string): Promise<ModelRun> {
  const response = await fetch(
    `${VIBEFORGE_BASE}/run/${runId}`,
    createFetchOptions()
  );
  return handleResponse<ModelRun>(response);
}

/**
 * Fetch run history with optional filtering
 *
 * Returns paginated list of previous runs. Useful for building history panels.
 *
 * @param options - Pagination and filter options
 * @returns Paginated run history
 *
 * @example
 * ```typescript
 * // Get most recent 10 runs
 * const history = await fetchHistory({ limit: 10, offset: 0 });
 *
 * // Filter by model and status
 * const claudeErrors = await fetchHistory({
 *   limit: 20,
 *   offset: 0,
 *   model: 'claude-3-opus-20240229',
 *   status: 'error',
 * });
 *
 * console.log(`Total runs: ${history.total}`);
 * console.log(`Showing: ${history.items.length}`);
 * ```
 */
export async function fetchHistory(
  options: {
    limit?: number;
    offset?: number;
    model?: string;
    status?: string;
  } = {}
): Promise<RunHistory> {
  const params = new URLSearchParams();
  if (options.limit !== undefined)
    params.append("limit", String(options.limit));
  if (options.offset !== undefined)
    params.append("offset", String(options.offset));
  if (options.model) params.append("model", options.model);
  if (options.status) params.append("status", options.status);

  const url = `${VIBEFORGE_BASE}/history?${params.toString()}`;
  const response = await fetch(url, createFetchOptions());
  return handleResponse<RunHistory>(response);
}

/**
 * List available models (future endpoint)
 *
 * Placeholder for model discovery. To be implemented in backend.
 */
export async function listModels(): Promise<string[]> {
  // For now, return hardcoded list
  // Future: implement /models endpoint in backend
  return [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "gpt-4-turbo-preview",
    "gpt-3.5-turbo",
    "ollama:mistral",
    "ollama:llama2",
  ];
}

/**
 * Export client as namespace for convenience
 */
export const vibeforgeClient = {
  healthCheck,
  postRun,
  getRun,
  fetchHistory,
  listModels,
};
````

### File: `src/lib/api/types.ts`

```typescript
/**
 * VibeForge API Type Definitions
 *
 * Keep these in sync with Pydantic models in vibeforge_models.py
 */

/**
 * Token usage statistics for a run
 */
export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/**
 * Context block for prompt construction
 *
 * Types: 'system' | 'design' | 'project' | 'code' | 'workflow'
 */
export interface ContextBlock {
  id: string;
  title: string;
  content: string;
  kind: string;
  priority: number;
}

/**
 * Run status enumeration
 */
export type RunStatus =
  | "pending"
  | "running"
  | "complete"
  | "error"
  | "cancelled";

/**
 * Request to create a new model run
 */
export interface CreateRunRequest {
  model: string;
  prompt: string;
  active_contexts?: ContextBlock[];
  data_profile_id?: string | null;
  eval_profile_id?: string | null;
}

/**
 * Complete model run record
 */
export interface ModelRun {
  id: string;
  model: string;
  prompt: string;
  status: RunStatus;
  output?: string | null;
  error?: string | null;
  tokens_used?: TokenUsage | null;
  created_at: string; // ISO 8601
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  active_contexts: ContextBlock[];
  data_profile_id?: string | null;
  eval_profile_id?: string | null;
}

/**
 * Paginated history response
 */
export interface RunHistory {
  total: number;
  limit: number;
  offset: number;
  items: ModelRun[];
}
```

---

## Integration Points

### 1. Workbench Run Button

**File**: `src/routes/workbench/+page.svelte`

```svelte
<script lang="ts">
  import { postRun, APIError } from '$lib/api/client';
  import type { ContextBlock, CreateRunRequest } from '$lib/api/types';

  let prompt = '';
  let activeContexts: ContextBlock[] = [];
  let selectedModel = 'claude-3-opus-20240229';
  let isLoading = false;
  let output = '';
  let error = '';

  async function handleRunClick() {
    if (!prompt.trim()) {
      error = 'Prompt cannot be empty';
      return;
    }

    isLoading = true;
    error = '';
    output = '';

    try {
      const request: CreateRunRequest = {
        model: selectedModel,
        prompt: prompt.trim(),
        active_contexts: activeContexts,
      };

      console.log('Sending run request:', request);
      const run = await postRun(request);

      console.log('Run completed:', run);
      output = run.output || '';

      // Show token usage
      if (run.tokens_used) {
        console.log(
          `Tokens used - Prompt: ${run.tokens_used.prompt_tokens}, ` +
          `Completion: ${run.tokens_used.completion_tokens}, ` +
          `Total: ${run.tokens_used.total_tokens}`
        );
      }
    } catch (err) {
      if (err instanceof APIError) {
        error = `API Error (${err.status}): ${err.details}`;
      } else {
        error = `Error: ${err instanceof Error ? err.message : 'Unknown error'}`;
      }
      console.error('Run failed:', error);
    } finally {
      isLoading = false;
    }
  }
</script>

<!-- Workbench UI -->
<div class="workbench">
  <!-- Model selector -->
  <select bind:value={selectedModel} disabled={isLoading}>
    <option value="claude-3-opus-20240229">Claude 3 Opus</option>
    <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
    <option value="gpt-4-turbo-preview">GPT-4 Turbo</option>
    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
  </select>

  <!-- Prompt input -->
  <textarea
    bind:value={prompt}
    placeholder="Enter your prompt..."
    disabled={isLoading}
  />

  <!-- Context blocks display -->
  <div class="contexts">
    {#each activeContexts as ctx (ctx.id)}
      <div class="context-item">
        <strong>{ctx.title}</strong>
        <p>{ctx.content.substring(0, 100)}...</p>
      </div>
    {/each}
  </div>

  <!-- Run button -->
  <button on:click={handleRunClick} disabled={isLoading}>
    {isLoading ? 'Running...' : 'Run'}
  </button>

  <!-- Error display -->
  {#if error}
    <div class="error-panel">
      {error}
    </div>
  {/if}

  <!-- Output panel -->
  {#if output}
    <div class="output-panel">
      <h3>Output</h3>
      <pre>{output}</pre>
    </div>
  {/if}
</div>

<style>
  .workbench {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  textarea {
    min-height: 200px;
    font-family: monospace;
  }

  .contexts {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 0.5rem;
  }

  .context-item {
    padding: 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: #f9f9f9;
  }

  .error-panel {
    padding: 1rem;
    background: #fee;
    border-left: 4px solid #f44;
    color: #c33;
  }

  .output-panel {
    padding: 1rem;
    background: #f0f0f0;
    border: 1px solid #ddd;
    border-radius: 4px;
  }

  .output-panel pre {
    margin: 0;
    overflow-x: auto;
  }
</style>
```

### 2. History Panel

**File**: `src/routes/history/+page.svelte`

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchHistory, APIError } from '$lib/api/client';
  import type { ModelRun } from '$lib/api/types';

  let runs: ModelRun[] = [];
  let total = 0;
  let isLoading = false;
  let error = '';
  let currentPage = 0;
  const pageSize = 10;

  async function loadHistory() {
    isLoading = true;
    error = '';

    try {
      const result = await fetchHistory({
        limit: pageSize,
        offset: currentPage * pageSize,
      });

      runs = result.items;
      total = result.total;
    } catch (err) {
      if (err instanceof APIError) {
        error = `API Error (${err.status}): ${err.details}`;
      } else {
        error = `Error: ${err instanceof Error ? err.message : 'Unknown error'}`;
      }
    } finally {
      isLoading = false;
    }
  }

  onMount(() => loadHistory());

  function previousPage() {
    if (currentPage > 0) {
      currentPage--;
      loadHistory();
    }
  }

  function nextPage() {
    if ((currentPage + 1) * pageSize < total) {
      currentPage++;
      loadHistory();
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString();
  }

  function formatDuration(ms?: number) {
    if (!ms) return '-';
    return `${(ms / 1000).toFixed(1)}s`;
  }
</script>

<div class="history-container">
  <h1>Run History</h1>

  {#if error}
    <div class="error-panel">{error}</div>
  {/if}

  {#if isLoading}
    <div class="loading">Loading...</div>
  {:else}
    <div class="runs-table">
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Tokens</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each runs as run (run.id)}
            <tr class="status-{run.status}">
              <td title={run.prompt.substring(0, 100)}>
                {run.model}
              </td>
              <td>
                <span class="status-badge {run.status}">
                  {run.status}
                </span>
              </td>
              <td>{formatDuration(run.duration_ms)}</td>
              <td>
                {#if run.tokens_used}
                  {run.tokens_used.total_tokens}
                {:else}
                  -
                {/if}
              </td>
              <td>{formatDate(run.created_at)}</td>
              <td>
                <a href="/run/{run.id}">View</a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button on:click={previousPage} disabled={currentPage === 0}>
        Previous
      </button>
      <span>
        Page {currentPage + 1} of {Math.ceil(total / pageSize)}
        ({total} total)
      </span>
      <button
        on:click={nextPage}
        disabled={(currentPage + 1) * pageSize >= total}
      >
        Next
      </button>
    </div>
  {/if}
</div>

<style>
  .history-container {
    padding: 2rem;
  }

  .error-panel {
    padding: 1rem;
    background: #fee;
    border-left: 4px solid #f44;
    color: #c33;
    margin-bottom: 1rem;
  }

  .runs-table {
    overflow-x: auto;
    margin: 1rem 0;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    text-align: left;
    padding: 0.75rem;
    border-bottom: 1px solid #ddd;
  }

  th {
    background: #f5f5f5;
    font-weight: 600;
  }

  .status-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .status-badge.complete {
    background: #d4edda;
    color: #155724;
  }

  .status-badge.error {
    background: #f8d7da;
    color: #721c24;
  }

  .status-badge.running,
  .status-badge.pending {
    background: #cce5ff;
    color: #004085;
  }

  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin-top: 1rem;
  }

  .pagination button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
```

### 3. Run Details Page

**File**: `src/routes/run/[id]/+page.svelte`

```svelte
<script lang="ts">
  import { page } from '$app/stores';
  import { getRun, APIError } from '$lib/api/client';
  import type { ModelRun } from '$lib/api/types';

  let run: ModelRun | null = null;
  let isLoading = true;
  let error = '';

  $: if ($page.params.id) {
    loadRun($page.params.id);
  }

  async function loadRun(runId: string) {
    isLoading = true;
    error = '';

    try {
      run = await getRun(runId);
    } catch (err) {
      if (err instanceof APIError) {
        error = `API Error (${err.status}): ${err.details}`;
      } else {
        error = `Error: ${err instanceof Error ? err.message : 'Unknown error'}`;
      }
    } finally {
      isLoading = false;
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString();
  }
</script>

<div class="run-details">
  {#if isLoading}
    <div class="loading">Loading...</div>
  {:else if error}
    <div class="error-panel">{error}</div>
  {:else if run}
    <h1>Run Details: {run.id}</h1>

    <div class="info-grid">
      <div class="info-item">
        <label>Model</label>
        <code>{run.model}</code>
      </div>
      <div class="info-item">
        <label>Status</label>
        <span class="status-badge {run.status}">{run.status}</span>
      </div>
      <div class="info-item">
        <label>Created</label>
        <time>{formatDate(run.created_at)}</time>
      </div>
      {#if run.duration_ms}
        <div class="info-item">
          <label>Duration</label>
          <span>{(run.duration_ms / 1000).toFixed(1)}s</span>
        </div>
      {/if}
    </div>

    {#if run.tokens_used}
      <div class="tokens-section">
        <h3>Token Usage</h3>
        <div class="token-stats">
          <div>
            <strong>Prompt:</strong> {run.tokens_used.prompt_tokens}
          </div>
          <div>
            <strong>Completion:</strong> {run.tokens_used.completion_tokens}
          </div>
          <div>
            <strong>Total:</strong> {run.tokens_used.total_tokens}
          </div>
        </div>
      </div>
    {/if}

    <div class="prompt-section">
      <h3>Prompt</h3>
      <pre>{run.prompt}</pre>
    </div>

    {#if run.output}
      <div class="output-section">
        <h3>Output</h3>
        <pre>{run.output}</pre>
      </div>
    {/if}

    {#if run.error}
      <div class="error-section">
        <h3>Error</h3>
        <pre>{run.error}</pre>
      </div>
    {/if}

    {#if run.active_contexts.length > 0}
      <div class="contexts-section">
        <h3>Active Contexts</h3>
        {#each run.active_contexts as ctx (ctx.id)}
          <div class="context-block">
            <h4>{ctx.title}</h4>
            <p class="kind">{ctx.kind}</p>
            <pre>{ctx.content}</pre>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .run-details {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin: 2rem 0;
  }

  .info-item {
    padding: 1rem;
    background: #f9f9f9;
    border-radius: 4px;
  }

  .info-item label {
    display: block;
    font-weight: 600;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #666;
  }

  .info-item code,
  .info-item time,
  .info-item span {
    font-family: monospace;
  }

  .status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .status-badge.complete {
    background: #d4edda;
    color: #155724;
  }

  .status-badge.error {
    background: #f8d7da;
    color: #721c24;
  }

  .status-badge.running,
  .status-badge.pending {
    background: #cce5ff;
    color: #004085;
  }

  .tokens-section,
  .prompt-section,
  .output-section,
  .error-section,
  .contexts-section {
    margin: 2rem 0;
  }

  .token-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin: 1rem 0;
  }

  .token-stats div {
    padding: 1rem;
    background: #f0f7ff;
    border-radius: 4px;
  }

  pre {
    background: #f5f5f5;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.875rem;
  }

  .context-block {
    margin: 1rem 0;
    padding: 1rem;
    border-left: 4px solid #007bff;
    background: #f0f7ff;
    border-radius: 4px;
  }

  .context-block h4 {
    margin: 0 0 0.25rem 0;
  }

  .context-block .kind {
    font-size: 0.875rem;
    color: #666;
    margin: 0 0 0.5rem 0;
  }

  .error-section {
    background: #fee;
    border-left: 4px solid #f44;
    padding: 1rem;
    border-radius: 4px;
  }
</style>
```

---

## Example Request/Response

### Request: Create Run

**Endpoint**: `POST /v1/vibeforge/run`

```json
{
  "model": "claude-3-opus-20240229",
  "prompt": "Analyze this TypeScript code for performance issues:\n\nfunction findDuplicates(arr: number[]): number[] {\n  const result = [];\n  for (let i = 0; i < arr.length; i++) {\n    for (let j = i + 1; j < arr.length; j++) {\n      if (arr[i] === arr[j]) result.push(arr[i]);\n    }\n  }\n  return result;\n}",
  "active_contexts": [
    {
      "id": "ctx-code-guidelines",
      "title": "Code Review Guidelines",
      "content": "- Focus on algorithmic efficiency (Big O complexity)\n- Flag any N² or worse algorithms\n- Suggest use of Set/Map for lookups\n- Consider edge cases and null safety",
      "kind": "code",
      "priority": 2
    },
    {
      "id": "ctx-typescript-style",
      "title": "TypeScript Best Practices",
      "content": "- Always use explicit return types\n- Prefer const over let\n- Use Set/Map instead of nested loops\n- Avoid any types",
      "kind": "code",
      "priority": 1
    }
  ],
  "data_profile_id": null,
  "eval_profile_id": null
}
```

### Response: Create Run (Success)

**Status**: 201 Created

````json
{
  "id": "run-abc123def456",
  "model": "claude-3-opus-20240229",
  "prompt": "Analyze this TypeScript code...",
  "status": "complete",
  "output": "# Performance Analysis\n\n## Issues Found:\n\n1. **O(n²) Nested Loop**: The function uses nested loops, making it O(n²) in time complexity. For large arrays, this becomes a bottleneck.\n\n2. **Duplicate Results**: If the input has multiple occurrences of the same number, they'll all be added to the result. You might want unique duplicates only.\n\n## Recommendations:\n\n```typescript\nfunction findDuplicates(arr: number[]): number[] {\n  const seen = new Set<number>();\n  const duplicates = new Set<number>();\n  \n  for (const num of arr) {\n    if (seen.has(num)) {\n      duplicates.add(num);\n    } else {\n      seen.add(num);\n    }\n  }\n  \n  return Array.from(duplicates);\n}\n```\n\nThis solution is O(n) time and O(n) space, much better for large arrays.",
  "error": null,
  "tokens_used": {
    "prompt_tokens": 187,
    "completion_tokens": 312,
    "total_tokens": 499
  },
  "created_at": "2025-11-18T14:30:00Z",
  "started_at": "2025-11-18T14:30:01Z",
  "completed_at": "2025-11-18T14:30:05Z",
  "duration_ms": 4200,
  "active_contexts": [
    {
      "id": "ctx-code-guidelines",
      "title": "Code Review Guidelines",
      "content": "- Focus on algorithmic efficiency (Big O complexity)\n- Flag any N² or worse algorithms\n- Suggest use of Set/Map for lookups\n- Consider edge cases and null safety",
      "kind": "code",
      "priority": 2
    },
    {
      "id": "ctx-typescript-style",
      "title": "TypeScript Best Practices",
      "content": "- Always use explicit return types\n- Prefer const over let\n- Use Set/Map instead of nested loops\n- Avoid any types",
      "kind": "code",
      "priority": 1
    }
  ],
  "data_profile_id": null,
  "eval_profile_id": null
}
````

### Response: Create Run (Error)

**Status**: 500 Internal Server Error

```json
{
  "detail": "Error: Anthropic API key not configured. Set ANTHROPIC_API_KEY in environment."
}
```

### Response: Get History

**Endpoint**: `GET /v1/vibeforge/history?limit=5&offset=0`

**Status**: 200 OK

```json
{
  "total": 42,
  "limit": 5,
  "offset": 0,
  "items": [
    {
      "id": "run-abc123def456",
      "model": "claude-3-opus-20240229",
      "prompt": "Analyze this TypeScript code...",
      "status": "complete",
      "output": "# Performance Analysis\n\n...",
      "error": null,
      "tokens_used": {
        "prompt_tokens": 187,
        "completion_tokens": 312,
        "total_tokens": 499
      },
      "created_at": "2025-11-18T14:30:00Z",
      "started_at": "2025-11-18T14:30:01Z",
      "completed_at": "2025-11-18T14:30:05Z",
      "duration_ms": 4200,
      "active_contexts": [],
      "data_profile_id": null,
      "eval_profile_id": null
    }
  ]
}
```

---

## Running Both Servers

### Terminal 1: Start Backend (FastAPI + Rust)

```bash
cd vibeforge-backend

# First time: Build Rust + install dependencies
maturin develop
pip install -e .[dev]

# Then start the server
uvicorn app.main:app --reload --port 8000
```

**Expected output**:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Check health:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"vibeforge-backend"}
```

### Terminal 2: Start Frontend (SvelteKit)

```bash
cd vibeforge  # SvelteKit project root

# First time: Install dependencies
pnpm install

# Create .env.local with PUBLIC_API_BASE_URL
echo 'PUBLIC_API_BASE_URL=http://localhost:8000' > .env.local

# Start dev server
pnpm dev
```

**Expected output**:

```
  VITE v4.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

Visit: http://localhost:5173/

### Verify CORS

Backend should allow frontend origin:

```bash
curl -X OPTIONS http://localhost:8000/v1/vibeforge/run \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

Should include in response:

```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: POST
```

---

## End-to-End Testing

### 1. Health Check

```bash
# Backend health
curl http://localhost:8000/health
# {"status":"ok","service":"vibeforge"}

# Frontend should load without errors
# Check browser console for any API errors
```

### 2. Test Workbench Run

**Via Frontend (Recommended)**:

1. Navigate to http://localhost:5173/workbench
2. Select model: "Claude 3 Opus"
3. Enter prompt: "What is the capital of France?"
4. Click "Run"
5. Verify output appears in output panel

**Via curl**:

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "What is the capital of France?",
    "active_contexts": []
  }'
```

### 3. Test History

Navigate to http://localhost:5173/history or via curl:

```bash
curl http://localhost:8000/v1/vibeforge/history?limit=5&offset=0
```

### 4. Test Run Details

1. Get a run ID from history
2. Navigate to http://localhost:5173/run/{run-id}
3. Verify all metadata displays correctly

### 5. Token Counting

Verify Rust token estimation is working:

```bash
python3 << 'EOF'
from vibeforge_prompt import estimate_tokens_precise

text = "The quick brown fox jumps over the lazy dog. " * 10
tokens = estimate_tokens_precise(text)
print(f"Text length: {len(text)} chars")
print(f"Estimated tokens: {tokens}")
EOF
```

---

## Troubleshooting

### CORS Errors in Browser Console

**Problem**: `Access-Control-Allow-Origin` error when calling API

**Solution**:

1. Verify backend has frontend origin in `CORS_ORIGINS`:

   ```python
   # vibeforge-backend/.env
   CORS_ORIGINS=["http://localhost:5173"]
   ```

2. Restart backend:

   ```bash
   # Stop: Ctrl+C in terminal 1
   uvicorn app.main:app --reload --port 8000
   ```

3. Clear browser cache (Ctrl+Shift+Delete in Chrome)

### API Not Found (404)

**Problem**: Frontend gets 404 when calling `/v1/vibeforge/run`

**Solution**:

1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `PUBLIC_API_BASE_URL` in frontend `.env.local`
3. Check API endpoint in `src/lib/api/client.ts` matches backend route

### API Key Errors

**Problem**: `"Anthropic API key not configured"`

**Solution**:

1. Set in backend `.env`:

   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

2. Restart backend (keys are loaded at startup)

### Rust Module Not Found

**Problem**: `ImportError: cannot import name 'estimate_tokens_precise'`

**Solution**:

```bash
cd vibeforge-backend
rm -rf rust/target
maturin develop
```

### Frontend Can't Connect to Backend

**Problem**: Frontend shows "Error: Cannot connect to API"

**Solution**:

1. Verify backend is running on port 8000
2. Check frontend URL: should be `http://localhost:8000` (not `https://`)
3. Check `.env.local`:
   ```
   PUBLIC_API_BASE_URL=http://localhost:8000
   ```

### Slow Token Estimation

**Problem**: Token counting takes >1s

**Solution**:

- This is the Rust debug build. Use release build:
  ```bash
  maturin develop --release
  ```

### Data Not Persisting

**Problem**: Runs created in one server restart are gone

**Solution**:

- This is expected with JSON storage. Data persists in `data/runs.json`
- To preserve data across restarts, backup `data/` directory:
  ```bash
  cp -r vibeforge-backend/data/ vibeforge-backend/data.backup/
  ```

---

## Next Steps

1. **Authentication**: Add JWT tokens to protect endpoints (see `.github/copilot-instructions.md`)
2. **Vector Database**: Integrate Qdrant for semantic search of past runs
3. **Real-time Updates**: Use WebSockets for streaming LLM responses
4. **Context Management**: Implement `/contexts` endpoints for CRUD operations
5. **Evaluation Profiles**: Implement `/evaluate` endpoints for run scoring

See `ARCHITECTURE.md` for design decisions and `DEPLOYMENT_GUIDE.md` for production setup.
