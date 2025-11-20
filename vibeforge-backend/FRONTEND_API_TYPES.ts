/**
 * VibeForge API Type Definitions
 *
 * Keep these in sync with Pydantic models in vibeforge_models.py
 * These types are used throughout the frontend for type safety.
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
 * Kinds: 'system' | 'design' | 'project' | 'code' | 'workflow'
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

/**
 * Standard API error response
 */
export interface APIErrorResponse {
  detail: string;
  status?: number;
}
