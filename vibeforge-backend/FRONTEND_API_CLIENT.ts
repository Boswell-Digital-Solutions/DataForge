/**
 * VibeForge API Client
 *
 * Provides type-safe HTTP methods for communicating with the FastAPI backend.
 * Handles token counting, run creation, and history retrieval.
 *
 * Place this in: src/lib/api/client.ts
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
 * The backend will:
 * 1. Create a pending run record
 * 2. Call the LLM service with your prompt + contexts
 * 3. Collect token usage statistics
 * 4. Return the completed run with output
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
 * Useful for implementing detail pages or polling for completion.
 *
 * @param runId - The ID of the run to retrieve
 * @returns The run with all metadata
 * @throws APIError if the run is not found
 *
 * @example
 * ```typescript
 * const run = await getRun('run-abc123');
 * console.log(`Status: ${run.status}`);
 * ```
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
 * Supports filtering by model and status for advanced UIs.
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
 * List available models
 *
 * Placeholder for model discovery. Future: implement /models endpoint in backend.
 * For now, returns hardcoded list of supported models.
 *
 * @returns Array of model identifiers
 */
export async function listModels(): Promise<string[]> {
  // Future: implement /models endpoint in backend
  // For now, return hardcoded list of supported models
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
