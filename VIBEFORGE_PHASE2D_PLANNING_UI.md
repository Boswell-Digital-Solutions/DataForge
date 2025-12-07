# VibeForge Phase 2D: Planning UI

**Goal:** Visual, controllable planning workflow in VibeForge  
**Estimated Time:** ~6 hours (Claude Code)  
**Test Coverage Required:** 100%  
**Target:** VibeForge (SvelteKit/Tauri)

---

## Quick Start

```bash
cd /path/to/vibeforge
pnpm check && pnpm test
claude --dangerously-skip-permissions
```

---

## Master Prompt

```
You are implementing Phase 2D for VibeForge - the Planning UI that provides a visual interface for the Cortex multi-AI orchestration system. This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 2.x with Svelte 5 runes, TypeScript, Tauri
- **Backend:** ForgeAgents Cortex API on port 8002
- **Styling:** Tailwind CSS with custom CSS variables
- **Testing:** Vitest for unit tests
- **Quality:** 100% test coverage is MANDATORY

## Execution Rules
1. Create git checkpoint after EACH task
2. Run `pnpm check && pnpm test` after EVERY file change
3. NEVER proceed if tests fail
4. Maintain 100% test coverage on all new code
5. Use Svelte 5 runes syntax ($state, $derived, $effect)
6. Follow existing VibeForge component patterns

---

## Phase 2D Deliverables

| Task | Deliverable | Location |
|------|-------------|----------|
| 1 | Cortex Client Service | src/lib/services/cortex.ts |
| 2 | Planning Types | src/lib/workbench/planning/types.ts |
| 3 | Planning Store | src/lib/workbench/planning/stores/planning.svelte.ts |
| 4 | RequestInput Component | src/lib/workbench/planning/components/RequestInput.svelte |
| 5 | CostEstimate Component | src/lib/workbench/planning/components/CostEstimate.svelte |
| 6 | StageCard Component | src/lib/workbench/planning/components/StageCard.svelte |
| 7 | PlanningStages Component | src/lib/workbench/planning/components/PlanningStages.svelte |
| 8 | PlanningControls Component | src/lib/workbench/planning/components/PlanningControls.svelte |
| 9 | FinalPlanViewer Component | src/lib/workbench/planning/components/FinalPlanViewer.svelte |
| 10 | PlanningPanel Component | src/lib/workbench/planning/components/PlanningPanel.svelte |
| 11 | Unit Tests | src/tests/planning/ |

---

## Task 1: Cortex Client Service

Create `src/lib/services/cortex.ts`:

```typescript
/**
 * Client service for Cortex Planning API
 */

export interface PlanningRequest {
  title: string;
  description: string;
  context?: string;
  pipeline?: 'default' | 'quick' | 'deep';
  maxIterations?: number;
  pauseAfterReview?: boolean;
  requireTestCoverage?: boolean;
  targetCoverage?: number;
}

export interface PipelineInfo {
  name: string;
  description: string;
  stagesCount: number;
  stages: Array<{
    type: string;
    provider: string;
    model: string;
  }>;
}

export interface SessionResponse {
  sessionId: string;
  status: string;
  pipeline: string;
  createdAt: string;
  stagesCount: number;
  currentStage: number;
  totalTokens: number;
  totalCost: number;
}

export interface StageInfo {
  index: number;
  type: string;
  provider: string;
  model: string;
  status: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  summary?: string;
  errorMessage?: string;
}

export interface Deliverable {
  implementationPlan: {
    content: string;
    filename: string;
    sections: string[];
  };
  claudeCodePrompt: {
    content: string;
    filename: string;
    phases: number;
    estimatedTime: string;
  };
  parseWarnings: string[];
}

export interface CostEstimate {
  pipeline: string;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
  estimatedCostMin: number;
  estimatedCostMax: number;
}

export interface SSEMessage {
  event: string;
  data: Record<string, unknown>;
}

type SSECallback = (message: SSEMessage) => void;

class CortexClient {
  private baseUrl: string;
  private eventSource: EventSource | null = null;

  constructor(baseUrl: string = 'http://localhost:8002/api/v1') {
    this.baseUrl = baseUrl;
  }

  // Pipeline info
  async listPipelines(): Promise<PipelineInfo[]> {
    const response = await fetch(`${this.baseUrl}/cortex/pipelines`);
    if (!response.ok) throw new Error(`Failed to list pipelines: ${response.statusText}`);
    return response.json();
  }

  async getPipeline(name: string): Promise<PipelineInfo> {
    const response = await fetch(`${this.baseUrl}/cortex/pipelines/${name}`);
    if (!response.ok) throw new Error(`Pipeline not found: ${name}`);
    return response.json();
  }

  // Cost estimation
  async estimateCost(request: PlanningRequest): Promise<CostEstimate> {
    const response = await fetch(`${this.baseUrl}/cortex/estimate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: request.title,
        description: request.description,
        context: request.context || '',
        pipeline: request.pipeline || 'default',
        max_iterations: request.maxIterations || 1,
        pause_after_review: request.pauseAfterReview || false,
        require_test_coverage: request.requireTestCoverage ?? true,
        target_coverage: request.targetCoverage ?? 100,
      }),
    });
    
    if (!response.ok) throw new Error(`Failed to estimate cost: ${response.statusText}`);
    
    const data = await response.json();
    return {
      pipeline: data.pipeline,
      estimatedInputTokens: data.estimated_input_tokens,
      estimatedOutputTokens: data.estimated_output_tokens,
      estimatedCostMin: data.estimated_cost_min,
      estimatedCostMax: data.estimated_cost_max,
    };
  }

  // Session management
  async startSession(request: PlanningRequest): Promise<SessionResponse> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: request.title,
        description: request.description,
        context: request.context || '',
        pipeline: request.pipeline || 'default',
        max_iterations: request.maxIterations || 1,
        pause_after_review: request.pauseAfterReview || false,
        require_test_coverage: request.requireTestCoverage ?? true,
        target_coverage: request.targetCoverage ?? 100,
      }),
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to start session: ${response.statusText}`);
    }
    
    const data = await response.json();
    return {
      sessionId: data.session_id,
      status: data.status,
      pipeline: data.pipeline,
      createdAt: data.created_at,
      stagesCount: data.stages_count,
      currentStage: data.current_stage,
      totalTokens: data.total_tokens,
      totalCost: data.total_cost,
    };
  }

  async getSession(sessionId: string): Promise<SessionResponse> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}`);
    if (!response.ok) throw new Error(`Session not found: ${sessionId}`);
    
    const data = await response.json();
    return {
      sessionId: data.session_id,
      status: data.status,
      pipeline: data.pipeline,
      createdAt: data.created_at,
      stagesCount: data.stages_count,
      currentStage: data.current_stage,
      totalTokens: data.total_tokens,
      totalCost: data.total_cost,
    };
  }

  async getSessionStages(sessionId: string): Promise<StageInfo[]> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}/stages`);
    if (!response.ok) throw new Error(`Failed to get stages: ${response.statusText}`);
    
    const data = await response.json();
    return data.map((s: Record<string, unknown>) => ({
      index: s.index,
      type: s.type,
      provider: s.provider,
      model: s.model,
      status: s.status,
      startedAt: s.started_at,
      completedAt: s.completed_at,
      durationMs: s.duration_ms,
      inputTokens: s.input_tokens,
      outputTokens: s.output_tokens,
      cost: s.cost,
      summary: s.summary,
      errorMessage: s.error_message,
    }));
  }

  async getStageOutput(sessionId: string, stageIndex: number): Promise<{ output: string; summary: string }> {
    const response = await fetch(
      `${this.baseUrl}/cortex/sessions/${sessionId}/stages/${stageIndex}/output`
    );
    if (!response.ok) throw new Error(`Failed to get stage output: ${response.statusText}`);
    return response.json();
  }

  async getDeliverable(sessionId: string): Promise<Deliverable> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}/deliverable`);
    if (!response.ok) throw new Error(`Failed to get deliverable: ${response.statusText}`);
    
    const data = await response.json();
    return {
      implementationPlan: {
        content: data.implementation_plan.content,
        filename: data.implementation_plan.filename,
        sections: data.implementation_plan.sections,
      },
      claudeCodePrompt: {
        content: data.claude_code_prompt.content,
        filename: data.claude_code_prompt.filename,
        phases: data.claude_code_prompt.phases,
        estimatedTime: data.claude_code_prompt.estimated_time,
      },
      parseWarnings: data.parse_warnings,
    };
  }

  // Session control
  async pauseSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}/pause`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`Failed to pause session: ${response.statusText}`);
  }

  async resumeSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}/resume`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`Failed to resume session: ${response.statusText}`);
  }

  async abortSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}/abort`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`Failed to abort session: ${response.statusText}`);
  }

  async injectContext(sessionId: string, stageIndex: number, context: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/cortex/sessions/${sessionId}/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage_index: stageIndex, context }),
    });
    if (!response.ok) throw new Error(`Failed to inject context: ${response.statusText}`);
  }

  // SSE Streaming
  startStreaming(request: PlanningRequest, callback: SSECallback): () => void {
    // For SSE, we need to use a different approach since we need POST
    // Use fetch with streaming reader
    const controller = new AbortController();
    
    (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/cortex/sessions/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: request.title,
            description: request.description,
            context: request.context || '',
            pipeline: request.pipeline || 'default',
            max_iterations: request.maxIterations || 1,
            pause_after_review: request.pauseAfterReview || false,
            require_test_coverage: request.requireTestCoverage ?? true,
            target_coverage: request.targetCoverage ?? 100,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Stream failed: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = '';
          let currentData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7);
            } else if (line.startsWith('data: ')) {
              currentData = line.slice(6);
            } else if (line === '' && currentEvent && currentData) {
              try {
                const data = JSON.parse(currentData);
                callback({ event: currentEvent, data });
              } catch (e) {
                console.error('Failed to parse SSE data:', e);
              }
              currentEvent = '';
              currentData = '';
            }
          }
        }
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          callback({ event: 'error', data: { error: (error as Error).message } });
        }
      }
    })();

    return () => controller.abort();
  }
}

export const cortexClient = new CortexClient();
export { CortexClient };
```

Checkpoint:
```bash
pnpm check && pnpm test
git add -A && git commit -m "feat(planning): Add Cortex client service"
git tag phase2d-task1-complete
```

---

## Task 2: Planning Types

Create `src/lib/workbench/planning/types.ts`:

```typescript
/**
 * Type definitions for Planning UI
 */

export type StageType = 'initial' | 'review' | 'refinement' | 'final';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type SessionStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'aborted';
export type PipelineType = 'default' | 'quick' | 'deep';

export interface PlanningRequestInput {
  title: string;
  description: string;
  context: string;
  pipeline: PipelineType;
  pauseAfterReview: boolean;
  requireTestCoverage: boolean;
  targetCoverage: number;
}

export interface Stage {
  index: number;
  type: StageType;
  provider: 'openai' | 'anthropic' | 'xai' | 'google';
  model: string;
  status: StageStatus;
  startedAt?: Date;
  completedAt?: Date;
  durationMs?: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  output?: string;
  summary?: string;
  errorMessage?: string;
  streamingOutput: string;
}

export interface TwoFileDeliverable {
  implementationPlan: {
    content: string;
    filename: string;
    sections: string[];
  };
  claudeCodePrompt: {
    content: string;
    filename: string;
    phases: number;
    estimatedTime: string;
  };
  parseWarnings: string[];
}

export interface PlanningSession {
  id: string;
  status: SessionStatus;
  pipeline: PipelineType;
  createdAt: Date;
  request: PlanningRequestInput;
  stages: Stage[];
  currentStageIndex: number;
  totalTokens: number;
  totalCost: number;
  finalPlan?: TwoFileDeliverable;
  errorMessage?: string;
}

export interface CostEstimate {
  pipeline: string;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
  estimatedCostMin: number;
  estimatedCostMax: number;
}

// Stage display info
export const STAGE_INFO: Record<StageType, { label: string; icon: string; description: string }> = {
  initial: {
    label: 'Initial Planning',
    icon: '📝',
    description: 'ChatGPT creates the initial implementation plan',
  },
  review: {
    label: 'Critical Review',
    icon: '🔍',
    description: 'Claude reviews and identifies improvements',
  },
  refinement: {
    label: 'Plan Refinement',
    icon: '🔧',
    description: 'ChatGPT addresses feedback and refines the plan',
  },
  final: {
    label: 'Final Deliverable',
    icon: '📦',
    description: 'Claude creates the two-file deliverable',
  },
};

export const PROVIDER_INFO: Record<string, { label: string; color: string }> = {
  openai: { label: 'OpenAI', color: '#10a37f' },
  anthropic: { label: 'Anthropic', color: '#d4a27f' },
  xai: { label: 'xAI', color: '#1da1f2' },
  google: { label: 'Google', color: '#4285f4' },
};

export const PIPELINE_INFO: Record<PipelineType, { label: string; description: string; stagesCount: number }> = {
  default: {
    label: 'Standard',
    description: '4-stage ChatGPT/Claude planning',
    stagesCount: 4,
  },
  quick: {
    label: 'Quick',
    description: 'Fast 2-stage pipeline',
    stagesCount: 2,
  },
  deep: {
    label: 'Deep',
    description: 'Extended with multiple reviews',
    stagesCount: 6,
  },
};
```

Checkpoint:
```bash
pnpm check && pnpm test
git add -A && git commit -m "feat(planning): Add planning types"
git tag phase2d-task2-complete
```

---

## Task 3: Planning Store

Create `src/lib/workbench/planning/stores/planning.svelte.ts`:

```typescript
/**
 * Planning Store - Svelte 5 Runes
 */
import { cortexClient, type SSEMessage } from '$lib/services/cortex';
import { licenseStore } from '$lib/core/stores/license.svelte';
import { FEATURES } from '$lib/core/types/license';
import type {
  PlanningSession,
  PlanningRequestInput,
  Stage,
  TwoFileDeliverable,
  CostEstimate,
  SessionStatus,
  StageStatus,
  PipelineType,
} from '../types';

class PlanningStore {
  // State
  sessions = $state<PlanningSession[]>([]);
  currentSession = $state<PlanningSession | null>(null);
  isLoading = $state(false);
  error = $state<string | null>(null);
  costEstimate = $state<CostEstimate | null>(null);

  // Private
  private _stopStreaming: (() => void) | null = null;

  // Derived
  currentStage = $derived(
    this.currentSession?.stages[this.currentSession.currentStageIndex] ?? null
  );
  
  progress = $derived(() => {
    if (!this.currentSession) return 0;
    const completed = this.currentSession.stages.filter(s => s.status === 'completed').length;
    return Math.round((completed / this.currentSession.stages.length) * 100);
  });

  isRunning = $derived(this.currentSession?.status === 'running');
  isPaused = $derived(this.currentSession?.status === 'paused');
  isComplete = $derived(this.currentSession?.status === 'completed');
  hasFailed = $derived(this.currentSession?.status === 'failed');

  canStart = $derived(
    !this.isLoading && 
    !this.isRunning && 
    licenseStore.hasFeature(FEATURES.ORCHESTRATOR_MULTI_AI)
  );

  totalCost = $derived(this.currentSession?.totalCost ?? 0);
  totalTokens = $derived(this.currentSession?.totalTokens ?? 0);

  // Actions
  async estimateCost(request: PlanningRequestInput): Promise<void> {
    try {
      this.costEstimate = await cortexClient.estimateCost({
        title: request.title,
        description: request.description,
        context: request.context,
        pipeline: request.pipeline,
        pauseAfterReview: request.pauseAfterReview,
        requireTestCoverage: request.requireTestCoverage,
        targetCoverage: request.targetCoverage,
      });
    } catch (e) {
      console.error('Failed to estimate cost:', e);
      this.costEstimate = null;
    }
  }

  async startSession(request: PlanningRequestInput): Promise<void> {
    if (!this.canStart) {
      this.error = 'Cannot start session: check license or current session';
      return;
    }

    this.isLoading = true;
    this.error = null;

    try {
      // Initialize session structure
      const session: PlanningSession = {
        id: '',
        status: 'pending',
        pipeline: request.pipeline,
        createdAt: new Date(),
        request,
        stages: this._initializeStages(request.pipeline),
        currentStageIndex: 0,
        totalTokens: 0,
        totalCost: 0,
      };

      this.currentSession = session;

      // Start streaming
      this._stopStreaming = cortexClient.startStreaming(
        {
          title: request.title,
          description: request.description,
          context: request.context,
          pipeline: request.pipeline,
          pauseAfterReview: request.pauseAfterReview,
          requireTestCoverage: request.requireTestCoverage,
          targetCoverage: request.targetCoverage,
        },
        (message) => this._handleSSEMessage(message)
      );
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to start session';
      this.currentSession = null;
    } finally {
      this.isLoading = false;
    }
  }

  async pause(): Promise<void> {
    if (!this.currentSession || !this.isRunning) return;

    try {
      await cortexClient.pauseSession(this.currentSession.id);
      this.currentSession.status = 'paused';
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to pause';
    }
  }

  async resume(): Promise<void> {
    if (!this.currentSession || !this.isPaused) return;

    try {
      await cortexClient.resumeSession(this.currentSession.id);
      this.currentSession.status = 'running';
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to resume';
    }
  }

  async abort(): Promise<void> {
    if (!this.currentSession) return;

    try {
      if (this._stopStreaming) {
        this._stopStreaming();
        this._stopStreaming = null;
      }
      await cortexClient.abortSession(this.currentSession.id);
      this.currentSession.status = 'aborted';
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to abort';
    }
  }

  async injectContext(stageIndex: number, context: string): Promise<void> {
    if (!this.currentSession) return;

    try {
      await cortexClient.injectContext(this.currentSession.id, stageIndex, context);
      // Update local state
      if (this.currentSession.stages[stageIndex]) {
        this.currentSession.stages[stageIndex].output = 
          (this.currentSession.stages[stageIndex].output || '') + `\n\n[User Context]: ${context}`;
      }
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to inject context';
    }
  }

  async loadDeliverable(): Promise<void> {
    if (!this.currentSession || !this.isComplete) return;

    try {
      const deliverable = await cortexClient.getDeliverable(this.currentSession.id);
      this.currentSession.finalPlan = deliverable;
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to load deliverable';
    }
  }

  async loadStageOutput(stageIndex: number): Promise<void> {
    if (!this.currentSession) return;

    try {
      const { output, summary } = await cortexClient.getStageOutput(
        this.currentSession.id,
        stageIndex
      );
      if (this.currentSession.stages[stageIndex]) {
        this.currentSession.stages[stageIndex].output = output;
        this.currentSession.stages[stageIndex].summary = summary;
      }
    } catch (e) {
      console.error('Failed to load stage output:', e);
    }
  }

  clearSession(): void {
    if (this._stopStreaming) {
      this._stopStreaming();
      this._stopStreaming = null;
    }
    this.currentSession = null;
    this.costEstimate = null;
    this.error = null;
  }

  clearError(): void {
    this.error = null;
  }

  // Private methods
  private _initializeStages(pipeline: PipelineType): Stage[] {
    const stageConfigs: Record<PipelineType, Array<{ type: Stage['type']; provider: Stage['provider']; model: string }>> = {
      default: [
        { type: 'initial', provider: 'openai', model: 'gpt-4o' },
        { type: 'review', provider: 'anthropic', model: 'claude-sonnet-4' },
        { type: 'refinement', provider: 'openai', model: 'gpt-4o' },
        { type: 'final', provider: 'anthropic', model: 'claude-sonnet-4' },
      ],
      quick: [
        { type: 'initial', provider: 'openai', model: 'gpt-4o-mini' },
        { type: 'final', provider: 'anthropic', model: 'claude-haiku' },
      ],
      deep: [
        { type: 'initial', provider: 'openai', model: 'gpt-4o' },
        { type: 'review', provider: 'anthropic', model: 'claude-sonnet-4' },
        { type: 'refinement', provider: 'openai', model: 'gpt-4o' },
        { type: 'review', provider: 'anthropic', model: 'claude-sonnet-4' },
        { type: 'refinement', provider: 'openai', model: 'gpt-4o' },
        { type: 'final', provider: 'anthropic', model: 'claude-sonnet-4' },
      ],
    };

    return stageConfigs[pipeline].map((config, index) => ({
      index,
      ...config,
      status: 'pending' as StageStatus,
      inputTokens: 0,
      outputTokens: 0,
      cost: 0,
      streamingOutput: '',
    }));
  }

  private _handleSSEMessage(message: SSEMessage): void {
    if (!this.currentSession) return;

    switch (message.event) {
      case 'session_started':
        this.currentSession.status = 'running';
        break;

      case 'stage_started': {
        const stageIndex = message.data.stage_index as number;
        this.currentSession.currentStageIndex = stageIndex;
        if (this.currentSession.stages[stageIndex]) {
          this.currentSession.stages[stageIndex].status = 'running';
          this.currentSession.stages[stageIndex].startedAt = new Date();
          this.currentSession.stages[stageIndex].streamingOutput = '';
        }
        break;
      }

      case 'stage_progress': {
        const stageIndex = message.data.stage_index as number;
        const token = message.data.token as string;
        if (this.currentSession.stages[stageIndex]) {
          this.currentSession.stages[stageIndex].streamingOutput += token;
        }
        break;
      }

      case 'stage_completed': {
        const stageIndex = message.data.stage_index as number;
        if (this.currentSession.stages[stageIndex]) {
          const stage = this.currentSession.stages[stageIndex];
          stage.status = 'completed';
          stage.completedAt = new Date();
          stage.durationMs = message.data.duration_ms as number;
          stage.inputTokens = (message.data.tokens as number) || 0;
          stage.outputTokens = 0;
          stage.cost = message.data.cost as number;
          stage.output = stage.streamingOutput;
          
          // Update totals
          this.currentSession.totalTokens += stage.inputTokens + stage.outputTokens;
          this.currentSession.totalCost += stage.cost;
        }
        break;
      }

      case 'stage_failed': {
        const stageIndex = message.data.stage_index as number;
        if (this.currentSession.stages[stageIndex]) {
          this.currentSession.stages[stageIndex].status = 'failed';
          this.currentSession.stages[stageIndex].errorMessage = message.data.error as string;
        }
        break;
      }

      case 'session_paused':
        this.currentSession.status = 'paused';
        break;

      case 'session_resumed':
        this.currentSession.status = 'running';
        break;

      case 'session_completed':
        this.currentSession.id = message.data.session_id as string;
        this.currentSession.status = 'completed';
        this.currentSession.totalTokens = message.data.total_tokens as number;
        this.currentSession.totalCost = message.data.total_cost as number;
        this._stopStreaming = null;
        // Auto-load deliverable
        this.loadDeliverable();
        break;

      case 'session_failed':
        this.currentSession.status = 'failed';
        this.currentSession.errorMessage = message.data.error as string;
        this.error = message.data.error as string;
        this._stopStreaming = null;
        break;

      case 'session_aborted':
        this.currentSession.status = 'aborted';
        this._stopStreaming = null;
        break;

      case 'error':
        this.error = message.data.error as string;
        break;
    }
  }
}

export const planningStore = new PlanningStore();
```

Checkpoint:
```bash
pnpm check && pnpm test
git add -A && git commit -m "feat(planning): Add planning store with SSE support"
git tag phase2d-task3-complete
```

---

## Task 4: RequestInput Component

Create `src/lib/workbench/planning/components/RequestInput.svelte`:

```svelte
<script lang="ts">
  import { planningStore } from '../stores/planning.svelte';
  import { PIPELINE_INFO, type PipelineType, type PlanningRequestInput } from '../types';
  import CostEstimate from './CostEstimate.svelte';

  interface Props {
    onCancel: () => void;
    onSubmit: () => void;
  }

  let { onCancel, onSubmit }: Props = $props();

  let title = $state('');
  let description = $state('');
  let context = $state('');
  let pipeline = $state<PipelineType>('default');
  let pauseAfterReview = $state(false);
  let requireTestCoverage = $state(true);
  let targetCoverage = $state(100);
  let showAdvanced = $state(false);

  const isValid = $derived(
    title.trim().length >= 3 && 
    description.trim().length >= 10
  );

  // Debounced cost estimation
  let estimateTimeout: ReturnType<typeof setTimeout>;
  $effect(() => {
    if (isValid) {
      clearTimeout(estimateTimeout);
      estimateTimeout = setTimeout(() => {
        planningStore.estimateCost({
          title, description, context, pipeline,
          pauseAfterReview, requireTestCoverage, targetCoverage,
        });
      }, 500);
    }
  });

  async function handleSubmit() {
    if (!isValid) return;

    const request: PlanningRequestInput = {
      title: title.trim(),
      description: description.trim(),
      context: context.trim(),
      pipeline,
      pauseAfterReview,
      requireTestCoverage,
      targetCoverage,
    };

    await planningStore.startSession(request);
    onSubmit();
  }
</script>

<div class="request-input">
  <h3>🎯 New Planning Session</h3>

  <div class="form-group">
    <label for="title">Feature Title</label>
    <input
      id="title"
      type="text"
      bind:value={title}
      placeholder="e.g., GitHub OAuth Integration"
      maxlength="200"
    />
    <span class="hint">{title.length}/200</span>
  </div>

  <div class="form-group">
    <label for="description">Description</label>
    <textarea
      id="description"
      bind:value={description}
      placeholder="Describe what you want to build. Include requirements, constraints, and any specific details..."
      rows="6"
    ></textarea>
    <span class="hint">Minimum 10 characters</span>
  </div>

  <div class="form-group">
    <label for="context">Additional Context (optional)</label>
    <textarea
      id="context"
      bind:value={context}
      placeholder="Existing code patterns, API docs, architectural decisions..."
      rows="4"
    ></textarea>
  </div>

  <div class="form-group">
    <label>Pipeline</label>
    <div class="pipeline-options">
      {#each Object.entries(PIPELINE_INFO) as [key, info]}
        <button
          class="pipeline-option"
          class:selected={pipeline === key}
          onclick={() => pipeline = key as PipelineType}
        >
          <span class="name">{info.label}</span>
          <span class="desc">{info.description}</span>
          <span class="stages">{info.stagesCount} stages</span>
        </button>
      {/each}
    </div>
  </div>

  <button
    class="toggle-advanced"
    onclick={() => showAdvanced = !showAdvanced}
  >
    {showAdvanced ? '▼' : '▶'} Advanced Options
  </button>

  {#if showAdvanced}
    <div class="advanced-options">
      <label class="checkbox-label">
        <input type="checkbox" bind:checked={pauseAfterReview} />
        Pause after review stage for context injection
      </label>

      <label class="checkbox-label">
        <input type="checkbox" bind:checked={requireTestCoverage} />
        Include test specifications
      </label>

      {#if requireTestCoverage}
        <div class="coverage-slider">
          <label>Target Coverage: {targetCoverage}%</label>
          <input
            type="range"
            min="40"
            max="100"
            step="20"
            bind:value={targetCoverage}
          />
        </div>
      {/if}
    </div>
  {/if}

  {#if planningStore.costEstimate}
    <CostEstimate estimate={planningStore.costEstimate} />
  {/if}

  <div class="actions">
    <button class="btn-secondary" onclick={onCancel}>
      Cancel
    </button>
    <button
      class="btn-primary"
      disabled={!isValid || planningStore.isLoading}
      onclick={handleSubmit}
    >
      {#if planningStore.isLoading}
        Starting...
      {:else}
        Start Planning
      {/if}
    </button>
  </div>
</div>

<style>
  .request-input {
    padding: 1.5rem;
    max-width: 600px;
  }

  h3 {
    margin: 0 0 1.5rem;
    font-size: 1.25rem;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  input[type="text"],
  textarea {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-1);
    color: var(--text-primary);
    font-size: 0.9375rem;
    resize: vertical;
  }

  input:focus,
  textarea:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-alpha);
  }

  .hint {
    display: block;
    margin-top: 0.25rem;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .pipeline-options {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
  }

  .pipeline-option {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    border: 2px solid var(--border);
    border-radius: 8px;
    background: var(--surface-1);
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
  }

  .pipeline-option:hover {
    border-color: var(--accent-light);
  }

  .pipeline-option.selected {
    border-color: var(--accent);
    background: var(--accent-alpha);
  }

  .pipeline-option .name {
    font-weight: 600;
    color: var(--text-primary);
  }

  .pipeline-option .desc {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin: 0.25rem 0;
  }

  .pipeline-option .stages {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .toggle-advanced {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.875rem;
    padding: 0.5rem 0;
  }

  .advanced-options {
    padding: 1rem;
    background: var(--surface-2);
    border-radius: 8px;
    margin: 0.5rem 0 1rem;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    font-weight: normal;
    cursor: pointer;
  }

  .coverage-slider {
    margin-top: 0.5rem;
    padding-left: 1.5rem;
  }

  .coverage-slider input {
    width: 100%;
    margin-top: 0.5rem;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
  }

  .btn-primary,
  .btn-secondary {
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background: var(--accent);
    color: white;
    border: none;
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: transparent;
    color: var(--text-primary);
    border: 1px solid var(--border);
  }
</style>
```

Checkpoint:
```bash
pnpm check && pnpm test
git add -A && git commit -m "feat(planning): Add RequestInput component"
git tag phase2d-task4-complete
```

---

## Tasks 5-11: Continue Implementation

Continue implementing the following components (create each with full functionality and styles):

**Task 5:** `CostEstimate.svelte` - Display cost estimate with min/max range

**Task 6:** `StageCard.svelte` - Individual stage display with status, progress, output preview

**Task 7:** `PlanningStages.svelte` - Vertical timeline of all stages

**Task 8:** `PlanningControls.svelte` - Pause/Resume/Abort buttons, context injection

**Task 9:** `FinalPlanViewer.svelte` - Two-tab view for Implementation Plan + Claude Code Prompt, with copy/download buttons

**Task 10:** `PlanningPanel.svelte` - Main panel orchestrating all components

**Task 11:** Unit tests for all stores and components (100% coverage)

---

## Final Checkpoint

```bash
pnpm check
pnpm test --coverage  # Must show 100%
git add -A && git commit -m "feat(planning): Complete Planning UI with 100% coverage"
git tag phase2d-complete
```

---

## Success Criteria

After completing Phase 2D:

- [ ] Can enter feature request details
- [ ] Pipeline selection works (default, quick, deep)
- [ ] Cost estimate displays before starting
- [ ] Session starts and shows progress
- [ ] Each stage shows streaming output
- [ ] Can pause/resume/abort session
- [ ] Can inject context before stages
- [ ] Final plan displays in two tabs
- [ ] Can copy implementation plan
- [ ] Can copy/download Claude Code prompt
- [ ] Error states handled gracefully
- [ ] 100% test coverage achieved
- [ ] pnpm check passes

---

## Integration

After Phase 2D, integrate the PlanningPanel into the main workbench layout:

1. Add planning tab to workbench sidebar
2. Wire keyboard shortcuts (Cmd+Shift+P for new planning session)
3. Add to analysis drawer for "Plan Implementation" action
4. Persist sessions to localStorage for recovery

Begin with Task 1. Execute each task completely, verify tests pass, create git checkpoint, then proceed to next task.
```
