# VibeForge Phase 2: Steps 5-6 Execution Guide (Continued)

This continues from Steps 1-4 in the main execution guide.

---

# Step 5: Planning Store (~1.5 hours)

## 5.1 Claude Code Prompt

```
You are implementing the Planning Store for VibeForge's Multi-AI Orchestrator (Cortex). This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 5, Svelte 5 runes, TypeScript, Tauri
- **Feature:** Planning session state management
- **Location:** src/lib/workbench/planning/stores/

## Execution Rules
1. Run `pnpm check && pnpm test` after EVERY file change
2. NEVER proceed if tests fail
3. Maintain 100% test coverage (Forge standard)
4. Use Svelte 5 runes ($state, $derived, $effect) - NO legacy stores

---

## Task 1: Create Planning Store

Create `src/lib/workbench/planning/stores/planning.svelte.ts`:

```typescript
import { browser } from '$app/environment';
import type {
  PlanningSession,
  PlanningStage,
  PlanningRequest,
  PlanningConfig,
  TwoFileDeliverable,
} from '../types';
import { DEFAULT_PLANNING_CONFIG } from '../types';
import { planningOrchestrator } from '../services/orchestrator';
import { licenseStore } from '$lib/core/stores/license.svelte';

interface PlanningState {
  sessions: PlanningSession[];
  currentSession: PlanningSession | null;
  isRunning: boolean;
  streamingOutput: string;
  error: string | null;
}

const STORAGE_KEY = 'vibeforge:planning:sessions';

class PlanningStore {
  private _state = $state<PlanningState>({
    sessions: [],
    currentSession: null,
    isRunning: false,
    streamingOutput: '',
    error: null,
  });

  // Getters
  get sessions() { return this._state.sessions; }
  get currentSession() { return this._state.currentSession; }
  get isRunning() { return this._state.isRunning; }
  get streamingOutput() { return this._state.streamingOutput; }
  get error() { return this._state.error; }

  // Derived: Current stage
  currentStage = $derived<PlanningStage | null>(() => {
    if (!this._state.currentSession) return null;
    return this._state.currentSession.stages[
      this._state.currentSession.currentStageIndex
    ] ?? null;
  });

  // Derived: Progress percentage
  progress = $derived<number>(() => {
    if (!this._state.currentSession) return 0;
    const { stages, currentStageIndex } = this._state.currentSession;
    if (stages.length === 0) return 0;
    
    const completedStages = stages.filter(s => s.status === 'completed').length;
    return Math.round((completedStages / stages.length) * 100);
  });

  // Derived: Total cost
  totalCost = $derived<number>(() => {
    if (!this._state.currentSession) return 0;
    return this._state.currentSession.stages.reduce(
      (sum, stage) => sum + (stage.cost ?? 0),
      0
    );
  });

  // Derived: Total tokens
  totalTokens = $derived<number>(() => {
    if (!this._state.currentSession) return 0;
    return this._state.currentSession.stages.reduce(
      (sum, stage) => sum + (stage.tokensUsed ?? 0),
      0
    );
  });

  // Derived: Can start new session
  canStartSession = $derived<boolean>(() => {
    return !this._state.isRunning && licenseStore.canUseOrchestrator;
  });

  // Derived: Is paused
  isPaused = $derived<boolean>(() => {
    return this._state.currentSession?.status === 'paused';
  });

  // Actions
  async startNewSession(
    request: PlanningRequest,
    config: Partial<PlanningConfig> = {}
  ): Promise<void> {
    if (!licenseStore.canUseOrchestrator) {
      this._state.error = 'Upgrade to Pro to use the Multi-AI Orchestrator';
      return;
    }

    this._state.isRunning = true;
    this._state.error = null;
    this._state.streamingOutput = '';

    const fullConfig = { ...DEFAULT_PLANNING_CONFIG, ...config };

    try {
      const session = await planningOrchestrator.startSession(
        request,
        fullConfig,
        {
          onStageStart: (stage) => {
            this._state.streamingOutput = '';
            this.updateSession();
          },
          onStageProgress: (stage, chunk) => {
            this._state.streamingOutput += chunk;
          },
          onStageComplete: (stage) => {
            this._state.streamingOutput = '';
            this.updateSession();
          },
          onStageFailed: (stage, error) => {
            this._state.error = error;
            this.updateSession();
          },
          onSessionComplete: (deliverable) => {
            this._state.isRunning = false;
            this.saveSession();
            licenseStore.incrementOrchestratorUsage();
          },
          onSessionFailed: (error) => {
            this._state.isRunning = false;
            this._state.error = error;
          },
        }
      );

      this._state.currentSession = session;
      this._state.sessions = [...this._state.sessions, session];
    } catch (error) {
      this._state.isRunning = false;
      this._state.error = error instanceof Error ? error.message : 'Unknown error';
    }
  }

  pause(): void {
    if (this._state.isRunning) {
      planningOrchestrator.pause();
      if (this._state.currentSession) {
        this._state.currentSession.status = 'paused';
      }
      this._state.isRunning = false;
    }
  }

  resume(): void {
    if (this._state.currentSession?.status === 'paused') {
      planningOrchestrator.resume();
      this._state.currentSession.status = 'active';
      this._state.isRunning = true;
    }
  }

  abort(): void {
    planningOrchestrator.abort();
    this._state.isRunning = false;
    if (this._state.currentSession) {
      this._state.currentSession.status = 'failed';
      this._state.currentSession.error = 'Aborted by user';
    }
  }

  injectContext(context: string): void {
    if (!this._state.currentSession) return;
    
    const nextIndex = this._state.currentSession.currentStageIndex + 1;
    planningOrchestrator.injectContext(
      this._state.currentSession,
      nextIndex,
      context
    );
  }

  loadSession(sessionId: string): void {
    const session = this._state.sessions.find(s => s.id === sessionId);
    if (session) {
      this._state.currentSession = session;
      this._state.error = null;
    }
  }

  deleteSession(sessionId: string): void {
    this._state.sessions = this._state.sessions.filter(s => s.id !== sessionId);
    if (this._state.currentSession?.id === sessionId) {
      this._state.currentSession = null;
    }
    this.persist();
  }

  clearError(): void {
    this._state.error = null;
  }

  clearCurrentSession(): void {
    this._state.currentSession = null;
    this._state.streamingOutput = '';
    this._state.error = null;
  }

  // Persistence
  private updateSession(): void {
    if (this._state.currentSession) {
      this._state.currentSession.updatedAt = new Date().toISOString();
    }
  }

  private saveSession(): void {
    if (this._state.currentSession) {
      const index = this._state.sessions.findIndex(
        s => s.id === this._state.currentSession!.id
      );
      if (index >= 0) {
        this._state.sessions[index] = this._state.currentSession;
      }
      this.persist();
    }
  }

  private persist(): void {
    if (browser) {
      const data = this._state.sessions.map(session => ({
        ...session,
        // Don't persist large streaming data
      }));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }
  }

  private loadFromStorage(): void {
    if (browser) {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          this._state.sessions = JSON.parse(stored);
        } catch {
          // Ignore parse errors
        }
      }
    }
  }

  // Constructor
  constructor() {
    this.loadFromStorage();
  }
}

export const planningStore = new PlanningStore();
```

---

## Task 2: Create Planning Store Tests

Create `src/tests/stores/planning.test.ts`:

```typescript
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

// Mock dependencies
vi.mock('$app/environment', () => ({
  browser: true
}));

vi.mock('$lib/core/stores/license.svelte', () => ({
  licenseStore: {
    canUseOrchestrator: true,
    incrementOrchestratorUsage: vi.fn(),
  },
}));

vi.mock('$lib/workbench/planning/services/orchestrator', () => ({
  planningOrchestrator: {
    startSession: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    abort: vi.fn(),
    injectContext: vi.fn(),
  },
}));

// Mock localStorage
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => localStorageMock.store[key] || null),
  setItem: vi.fn((key: string, value: string) => { localStorageMock.store[key] = value; }),
  clear: vi.fn(() => { localStorageMock.store = {}; })
};
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

import { planningStore } from '$lib/workbench/planning/stores/planning.svelte';
import { planningOrchestrator } from '$lib/workbench/planning/services/orchestrator';
import { licenseStore } from '$lib/core/stores/license.svelte';
import type { PlanningRequest, PlanningSession } from '$lib/workbench/planning/types';

const mockOrchestrator = vi.mocked(planningOrchestrator);
const mockLicenseStore = vi.mocked(licenseStore);

describe('PlanningStore', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    mockLicenseStore.canUseOrchestrator = true;
  });

  describe('startNewSession', () => {
    it('starts a new planning session', async () => {
      const mockSession: PlanningSession = {
        id: 'session-1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        status: 'completed',
        request: { type: 'feature', title: 'Test', description: 'Test' },
        config: {} as any,
        stages: [],
        currentStageIndex: 0,
      };

      mockOrchestrator.startSession.mockResolvedValueOnce(mockSession);

      const request: PlanningRequest = {
        type: 'feature',
        title: 'Test Feature',
        description: 'Test description',
      };

      await planningStore.startNewSession(request);

      expect(mockOrchestrator.startSession).toHaveBeenCalled();
      expect(planningStore.currentSession).toBeDefined();
    });

    it('blocks session start without license', async () => {
      mockLicenseStore.canUseOrchestrator = false;

      const request: PlanningRequest = {
        type: 'feature',
        title: 'Test',
        description: 'Test',
      };

      await planningStore.startNewSession(request);

      expect(mockOrchestrator.startSession).not.toHaveBeenCalled();
      expect(planningStore.error).toContain('Upgrade');
    });
  });

  describe('pause and resume', () => {
    it('pauses the orchestrator', () => {
      planningStore.pause();
      expect(mockOrchestrator.pause).toHaveBeenCalled();
    });

    it('resumes the orchestrator', () => {
      // Set up a paused session
      (planningStore as any)._state.currentSession = {
        status: 'paused',
      };

      planningStore.resume();
      expect(mockOrchestrator.resume).toHaveBeenCalled();
    });
  });

  describe('abort', () => {
    it('aborts the orchestrator', () => {
      planningStore.abort();
      expect(mockOrchestrator.abort).toHaveBeenCalled();
      expect(planningStore.isRunning).toBe(false);
    });
  });

  describe('injectContext', () => {
    it('injects context into next stage', () => {
      (planningStore as any)._state.currentSession = {
        currentStageIndex: 0,
      };

      planningStore.injectContext('Additional context');

      expect(mockOrchestrator.injectContext).toHaveBeenCalledWith(
        expect.anything(),
        1,
        'Additional context'
      );
    });
  });

  describe('deleteSession', () => {
    it('removes session from list', () => {
      const session: PlanningSession = {
        id: 'session-to-delete',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        status: 'completed',
        request: { type: 'feature', title: 'Test', description: 'Test' },
        config: {} as any,
        stages: [],
        currentStageIndex: 0,
      };

      (planningStore as any)._state.sessions = [session];
      (planningStore as any)._state.currentSession = session;

      planningStore.deleteSession('session-to-delete');

      expect(planningStore.sessions).toHaveLength(0);
      expect(planningStore.currentSession).toBeNull();
    });
  });

  describe('derived values', () => {
    it('calculates progress correctly', () => {
      (planningStore as any)._state.currentSession = {
        stages: [
          { status: 'completed' },
          { status: 'completed' },
          { status: 'running' },
          { status: 'pending' },
        ],
        currentStageIndex: 2,
      };

      expect(planningStore.progress()).toBe(50);
    });

    it('calculates total cost', () => {
      (planningStore as any)._state.currentSession = {
        stages: [
          { cost: 0.01 },
          { cost: 0.02 },
          { cost: 0.03 },
        ],
      };

      expect(planningStore.totalCost()).toBeCloseTo(0.06);
    });

    it('calculates total tokens', () => {
      (planningStore as any)._state.currentSession = {
        stages: [
          { tokensUsed: 100 },
          { tokensUsed: 200 },
          { tokensUsed: 300 },
        ],
      };

      expect(planningStore.totalTokens()).toBe(600);
    });
  });
});
```

---

## Task 3: Verify and Checkpoint

```bash
pnpm check
pnpm test src/tests/stores/planning.test.ts

git add -A
git commit -m "feat(planning): Add Planning Store for session state management"
git tag step-5-store-complete
```

**GATE:** All tests pass. Do not proceed until gate passes.
```

---

# Step 6: Planning UI Components (~3 hours)

## 6.1 Claude Code Prompt

```
You are implementing the Planning UI Components for VibeForge's Multi-AI Orchestrator (Cortex). This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 5, Svelte 5 runes, TypeScript, Tauri
- **Feature:** Multi-AI planning workflow UI
- **Location:** src/lib/workbench/planning/components/

## Execution Rules
1. Run `pnpm check && pnpm test` after EVERY file change
2. NEVER proceed if tests fail
3. Maintain 100% test coverage (Forge standard)
4. Use Svelte 5 syntax (runes, snippets)

---

## Task 1: Create PlanningPanel Component

Create `src/lib/workbench/planning/components/PlanningPanel.svelte`:

```svelte
<script lang="ts">
  import { planningStore } from '../stores/planning.svelte';
  import { licenseStore } from '$lib/core/stores/license.svelte';
  import PlanningStages from './PlanningStages.svelte';
  import RequestInput from './RequestInput.svelte';
  import PlanningControls from './PlanningControls.svelte';
  import FinalPlanViewer from './FinalPlanViewer.svelte';
  import UpgradePrompt from '$lib/components/UpgradePrompt.svelte';
  import { FEATURES } from '$lib/core/types/license';

  let showRequestInput = $state(false);
</script>

<div class="planning-panel">
  <header class="panel-header">
    <h2>🧠 Multi-AI Orchestrator</h2>
    <p class="subtitle">Cortex Planning System</p>
  </header>

  {#if !licenseStore.canUseOrchestrator}
    <UpgradePrompt feature={FEATURES.ORCHESTRATOR_MULTI_AI} />
  {:else if planningStore.currentSession?.finalPlan}
    <FinalPlanViewer deliverable={planningStore.currentSession.finalPlan} />
  {:else if planningStore.isRunning || planningStore.currentSession}
    <PlanningStages />
    <PlanningControls />
  {:else if showRequestInput}
    <RequestInput 
      onCancel={() => showRequestInput = false}
      onSubmit={() => showRequestInput = false}
    />
  {:else}
    <div class="empty-state">
      <div class="empty-icon">🎯</div>
      <h3>Start a Planning Session</h3>
      <p>
        Describe what you want to build and let ChatGPT and Claude 
        collaborate to create a comprehensive implementation plan.
      </p>
      <button class="start-btn" onclick={() => showRequestInput = true}>
        Start Planning
      </button>
      
      {#if planningStore.sessions.length > 0}
        <div class="recent-sessions">
          <h4>Recent Sessions</h4>
          {#each planningStore.sessions.slice(-5).reverse() as session (session.id)}
            <button 
              class="session-item"
              onclick={() => planningStore.loadSession(session.id)}
            >
              <span class="session-title">{session.request.title}</span>
              <span class="session-status" class:completed={session.status === 'completed'}>
                {session.status}
              </span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if planningStore.error}
    <div class="error-banner">
      <span>⚠️ {planningStore.error}</span>
      <button onclick={() => planningStore.clearError()}>Dismiss</button>
    </div>
  {/if}
</div>

<style>
  .planning-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--surface-primary);
  }

  .panel-header {
    padding: 1rem;
    border-bottom: 1px solid var(--border-primary);
  }

  .panel-header h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .subtitle {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    margin: 0.25rem 0 0;
  }

  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    text-align: center;
  }

  .empty-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .empty-state h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.5rem;
  }

  .empty-state p {
    color: var(--text-secondary);
    max-width: 24rem;
    margin: 0 0 1.5rem;
  }

  .start-btn {
    padding: 0.75rem 1.5rem;
    background: var(--ember-500);
    color: white;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .start-btn:hover {
    background: var(--ember-600);
  }

  .recent-sessions {
    margin-top: 2rem;
    width: 100%;
    max-width: 24rem;
  }

  .recent-sessions h4 {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    margin-bottom: 0.75rem;
  }

  .session-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0.75rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: border-color 0.15s ease;
  }

  .session-item:hover {
    border-color: var(--ember-500);
  }

  .session-title {
    font-weight: 500;
    color: var(--text-primary);
    text-align: left;
  }

  .session-status {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    text-transform: capitalize;
  }

  .session-status.completed {
    color: var(--green-400);
  }

  .error-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--red-900);
    color: var(--red-200);
    font-size: 0.875rem;
  }

  .error-banner button {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    text-decoration: underline;
  }
</style>
```

---

## Task 2: Create RequestInput Component

Create `src/lib/workbench/planning/components/RequestInput.svelte`:

```svelte
<script lang="ts">
  import { planningStore } from '../stores/planning.svelte';
  import type { RequestType, PlanningConfig } from '../types';
  import { DEFAULT_PLANNING_CONFIG } from '../types';
  import { Button } from '$lib/components/ui';

  interface Props {
    onCancel: () => void;
    onSubmit: () => void;
  }

  let { onCancel, onSubmit }: Props = $props();

  let requestType = $state<RequestType>('feature');
  let title = $state('');
  let description = $state('');
  let context = $state('');
  let showAdvanced = $state(false);
  let config = $state<Partial<PlanningConfig>>({});

  async function handleSubmit() {
    if (!title.trim() || !description.trim()) return;

    await planningStore.startNewSession(
      {
        type: requestType,
        title: title.trim(),
        description: description.trim(),
        context: context.trim() || undefined,
      },
      config
    );

    onSubmit();
  }
</script>

<div class="request-input">
  <h3>What do you want to build?</h3>

  <div class="form-group">
    <label for="request-type">Type</label>
    <div class="type-buttons">
      {#each ['feature', 'refactor', 'bugfix', 'analysis'] as type}
        <button
          class="type-btn"
          class:selected={requestType === type}
          onclick={() => requestType = type as RequestType}
        >
          {type}
        </button>
      {/each}
    </div>
  </div>

  <div class="form-group">
    <label for="title">Title</label>
    <input
      id="title"
      type="text"
      bind:value={title}
      placeholder="e.g., Add GitHub OAuth integration"
      class="text-input"
    />
  </div>

  <div class="form-group">
    <label for="description">Description</label>
    <textarea
      id="description"
      bind:value={description}
      placeholder="Describe what you want in detail. The more specific, the better the plan."
      rows="6"
      class="text-input"
    ></textarea>
  </div>

  <div class="form-group">
    <label for="context">Additional Context (optional)</label>
    <textarea
      id="context"
      bind:value={context}
      placeholder="Any relevant code, constraints, or preferences..."
      rows="3"
      class="text-input"
    ></textarea>
  </div>

  <button 
    class="advanced-toggle"
    onclick={() => showAdvanced = !showAdvanced}
  >
    {showAdvanced ? '▼' : '▶'} Advanced Options
  </button>

  {#if showAdvanced}
    <div class="advanced-options">
      <div class="form-row">
        <label>
          <span>Max Iterations</span>
          <select bind:value={config.maxIterations}>
            <option value={1}>1 (Quick)</option>
            <option value={2}>2 (Standard)</option>
            <option value={3}>3 (Thorough)</option>
          </select>
        </label>

        <label>
          <span>Test Coverage Target</span>
          <select bind:value={config.targetCoverage}>
            <option value={40}>40%</option>
            <option value={60}>60%</option>
            <option value={80}>80%</option>
            <option value={100}>100% (Recommended)</option>
          </select>
        </label>
      </div>

      <label class="checkbox-label">
        <input type="checkbox" bind:checked={config.pauseAfterReview} />
        <span>Pause after Claude's review for manual inspection</span>
      </label>
    </div>
  {/if}

  <div class="form-actions">
    <Button variant="ghost" onclick={onCancel}>
      Cancel
    </Button>
    <Button 
      variant="primary" 
      onclick={handleSubmit}
      disabled={!title.trim() || !description.trim() || planningStore.isRunning}
    >
      {planningStore.isRunning ? 'Starting...' : 'Start Planning'}
    </Button>
  </div>
</div>

<style>
  .request-input {
    padding: 1.5rem;
    overflow-y: auto;
  }

  h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 1.5rem;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  .form-group label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .type-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .type-btn {
    padding: 0.5rem 1rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    color: var(--text-secondary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease;
    text-transform: capitalize;
  }

  .type-btn:hover {
    border-color: var(--ember-500);
  }

  .type-btn.selected {
    background: var(--ember-500);
    border-color: var(--ember-500);
    color: white;
  }

  .text-input {
    width: 100%;
    padding: 0.625rem 0.75rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    resize: vertical;
  }

  .text-input:focus {
    outline: none;
    border-color: var(--ember-500);
  }

  .advanced-toggle {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 0.875rem;
    cursor: pointer;
    padding: 0.5rem 0;
  }

  .advanced-toggle:hover {
    color: var(--text-primary);
  }

  .advanced-options {
    padding: 1rem;
    background: var(--surface-secondary);
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .form-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .form-row label {
    flex: 1;
  }

  .form-row label span {
    display: block;
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-bottom: 0.25rem;
  }

  .form-row select {
    width: 100%;
    padding: 0.5rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-primary);
  }
</style>
```

---

## Task 3: Create PlanningStages Component

Create `src/lib/workbench/planning/components/PlanningStages.svelte`:

```svelte
<script lang="ts">
  import { planningStore } from '../stores/planning.svelte';
  import StageCard from './StageCard.svelte';
  import { getProviderLabel } from '../types';
</script>

<div class="planning-stages">
  <div class="progress-header">
    <div class="progress-info">
      <span class="progress-label">Progress</span>
      <span class="progress-value">{planningStore.progress()}%</span>
    </div>
    <div class="progress-bar">
      <div 
        class="progress-fill" 
        style="width: {planningStore.progress()}%"
      ></div>
    </div>
  </div>

  <div class="metrics">
    <div class="metric">
      <span class="metric-label">Cost</span>
      <span class="metric-value">${planningStore.totalCost().toFixed(4)}</span>
    </div>
    <div class="metric">
      <span class="metric-label">Tokens</span>
      <span class="metric-value">{planningStore.totalTokens().toLocaleString()}</span>
    </div>
  </div>

  <div class="stages-list">
    {#each planningStore.currentSession?.stages ?? [] as stage, index (stage.id)}
      <StageCard 
        {stage} 
        isActive={index === planningStore.currentSession?.currentStageIndex}
        streamingOutput={
          index === planningStore.currentSession?.currentStageIndex
            ? planningStore.streamingOutput
            : undefined
        }
      />
    {/each}
  </div>
</div>

<style>
  .planning-stages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
  }

  .progress-header {
    margin-bottom: 1rem;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }

  .progress-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .progress-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--ember-400);
  }

  .progress-bar {
    height: 0.5rem;
    background: var(--surface-secondary);
    border-radius: 0.25rem;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--ember-500);
    transition: width 0.3s ease;
  }

  .metrics {
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
    padding: 0.75rem;
    background: var(--surface-secondary);
    border-radius: 0.5rem;
  }

  .metric {
    display: flex;
    flex-direction: column;
  }

  .metric-label {
    font-size: 0.625rem;
    color: var(--text-tertiary);
    text-transform: uppercase;
  }

  .metric-value {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .stages-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
</style>
```

---

## Task 4: Create StageCard Component

Create `src/lib/workbench/planning/components/StageCard.svelte`:

```svelte
<script lang="ts">
  import type { PlanningStage } from '../types';
  import { getStageLabel, getProviderLabel } from '../types';

  interface Props {
    stage: PlanningStage;
    isActive: boolean;
    streamingOutput?: string;
  }

  let { stage, isActive, streamingOutput }: Props = $props();

  let expanded = $state(false);

  const statusIcons: Record<string, string> = {
    pending: '○',
    running: '◐',
    completed: '●',
    failed: '✗',
    skipped: '◌',
  };

  const statusColors: Record<string, string> = {
    pending: 'var(--text-tertiary)',
    running: 'var(--ember-400)',
    completed: 'var(--green-400)',
    failed: 'var(--red-400)',
    skipped: 'var(--text-tertiary)',
  };
</script>

<div 
  class="stage-card" 
  class:active={isActive}
  class:completed={stage.status === 'completed'}
>
  <button class="stage-header" onclick={() => expanded = !expanded}>
    <span class="status-icon" style="color: {statusColors[stage.status]}">
      {statusIcons[stage.status]}
    </span>
    <div class="stage-info">
      <span class="stage-label">{getStageLabel(stage)}</span>
      <span class="stage-model">
        {getProviderLabel(stage.provider)} · {stage.model}
      </span>
    </div>
    <div class="stage-meta">
      {#if stage.duration}
        <span class="duration">{(stage.duration / 1000).toFixed(1)}s</span>
      {/if}
      {#if stage.cost}
        <span class="cost">${stage.cost.toFixed(4)}</span>
      {/if}
      <span class="expand-icon">{expanded ? '▼' : '▶'}</span>
    </div>
  </button>

  {#if expanded || (isActive && stage.status === 'running')}
    <div class="stage-content">
      {#if isActive && stage.status === 'running' && streamingOutput}
        <pre class="output streaming">{streamingOutput}</pre>
      {:else if stage.output}
        <pre class="output">{stage.output}</pre>
      {:else if stage.status === 'pending'}
        <p class="pending-message">Waiting for previous stages to complete...</p>
      {:else if stage.status === 'failed'}
        <p class="error-message">Stage failed. Check error details above.</p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .stage-card {
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .stage-card.active {
    border-color: var(--ember-500);
  }

  .stage-card.completed {
    border-color: var(--green-900);
  }

  .stage-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
  }

  .status-icon {
    font-size: 1rem;
    width: 1rem;
    text-align: center;
  }

  .stage-info {
    flex: 1;
  }

  .stage-label {
    display: block;
    font-weight: 500;
    color: var(--text-primary);
    font-size: 0.875rem;
  }

  .stage-model {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .stage-meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .duration, .cost {
    font-family: var(--font-mono);
  }

  .expand-icon {
    color: var(--text-tertiary);
    font-size: 0.625rem;
  }

  .stage-content {
    padding: 0 0.75rem 0.75rem;
    border-top: 1px solid var(--border-primary);
  }

  .output {
    margin: 0.75rem 0 0;
    padding: 0.75rem;
    background: var(--surface-tertiary);
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 20rem;
    overflow-y: auto;
  }

  .output.streaming {
    border-left: 2px solid var(--ember-500);
  }

  .pending-message, .error-message {
    margin: 0.75rem 0 0;
    font-size: 0.875rem;
    color: var(--text-tertiary);
    font-style: italic;
  }

  .error-message {
    color: var(--red-400);
  }
</style>
```

---

## Task 5: Create PlanningControls Component

Create `src/lib/workbench/planning/components/PlanningControls.svelte`:

```svelte
<script lang="ts">
  import { planningStore } from '../stores/planning.svelte';
  import { Button } from '$lib/components/ui';

  let showContextInput = $state(false);
  let contextToInject = $state('');

  function handleInjectContext() {
    if (contextToInject.trim()) {
      planningStore.injectContext(contextToInject.trim());
      contextToInject = '';
      showContextInput = false;
    }
  }
</script>

<div class="planning-controls">
  {#if showContextInput}
    <div class="context-input">
      <textarea
        bind:value={contextToInject}
        placeholder="Add context for the next stage..."
        rows="3"
      ></textarea>
      <div class="context-actions">
        <Button variant="ghost" size="sm" onclick={() => showContextInput = false}>
          Cancel
        </Button>
        <Button variant="primary" size="sm" onclick={handleInjectContext}>
          Inject Context
        </Button>
      </div>
    </div>
  {:else}
    <div class="control-buttons">
      {#if planningStore.isRunning}
        <Button variant="secondary" onclick={() => planningStore.pause()}>
          ⏸ Pause
        </Button>
        <Button variant="ghost" onclick={() => showContextInput = true}>
          💬 Add Context
        </Button>
        <Button variant="ghost" onclick={() => planningStore.abort()}>
          ✗ Abort
        </Button>
      {:else if planningStore.isPaused()}
        <Button variant="primary" onclick={() => planningStore.resume()}>
          ▶ Resume
        </Button>
        <Button variant="ghost" onclick={() => showContextInput = true}>
          💬 Add Context
        </Button>
        <Button variant="ghost" onclick={() => planningStore.abort()}>
          ✗ Abort
        </Button>
      {:else if planningStore.currentSession?.status === 'completed'}
        <Button variant="primary" onclick={() => planningStore.clearCurrentSession()}>
          Start New Session
        </Button>
      {:else if planningStore.currentSession?.status === 'failed'}
        <Button variant="primary" onclick={() => planningStore.clearCurrentSession()}>
          Try Again
        </Button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .planning-controls {
    padding: 1rem;
    border-top: 1px solid var(--border-primary);
    background: var(--surface-secondary);
  }

  .control-buttons {
    display: flex;
    gap: 0.75rem;
  }

  .context-input {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .context-input textarea {
    width: 100%;
    padding: 0.625rem 0.75rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    resize: vertical;
  }

  .context-input textarea:focus {
    outline: none;
    border-color: var(--ember-500);
  }

  .context-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }
</style>
```

---

## Task 6: Create FinalPlanViewer Component

Create `src/lib/workbench/planning/components/FinalPlanViewer.svelte`:

```svelte
<script lang="ts">
  import type { TwoFileDeliverable } from '../types';
  import { planningStore } from '../stores/planning.svelte';
  import { Button } from '$lib/components/ui';

  interface Props {
    deliverable: TwoFileDeliverable;
  }

  let { deliverable }: Props = $props();

  let activeTab = $state<'plan' | 'prompt'>('plan');

  async function copyToClipboard(text: string) {
    await navigator.clipboard.writeText(text);
    // Could add a toast notification here
  }

  function downloadFile(content: string, filename: string) {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="final-plan-viewer">
  <div class="viewer-header">
    <h3>📄 Final Deliverable</h3>
    <Button variant="ghost" size="sm" onclick={() => planningStore.clearCurrentSession()}>
      New Session
    </Button>
  </div>

  <div class="tabs">
    <button 
      class="tab" 
      class:active={activeTab === 'plan'}
      onclick={() => activeTab = 'plan'}
    >
      Implementation Plan
    </button>
    <button 
      class="tab" 
      class:active={activeTab === 'prompt'}
      onclick={() => activeTab = 'prompt'}
    >
      Claude Code Prompt
    </button>
  </div>

  <div class="content">
    {#if activeTab === 'plan'}
      <div class="content-header">
        <span class="filename">{deliverable.implementationPlan.filename}</span>
        <div class="content-actions">
          <Button 
            variant="ghost" 
            size="sm" 
            onclick={() => copyToClipboard(deliverable.implementationPlan.content)}
          >
            📋 Copy
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            onclick={() => downloadFile(
              deliverable.implementationPlan.content, 
              deliverable.implementationPlan.filename
            )}
          >
            ⬇ Download
          </Button>
        </div>
      </div>
      
      {#if deliverable.implementationPlan.sections.length > 0}
        <nav class="sections-nav">
          {#each deliverable.implementationPlan.sections as section}
            <span class="section-link">{section}</span>
          {/each}
        </nav>
      {/if}
      
      <pre class="content-body">{deliverable.implementationPlan.content}</pre>
    {:else}
      <div class="content-header">
        <span class="filename">{deliverable.claudeCodePrompt.filename}</span>
        <div class="content-actions">
          <Button 
            variant="ghost" 
            size="sm" 
            onclick={() => copyToClipboard(deliverable.claudeCodePrompt.content)}
          >
            📋 Copy
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            onclick={() => downloadFile(
              deliverable.claudeCodePrompt.content, 
              deliverable.claudeCodePrompt.filename
            )}
          >
            ⬇ Download
          </Button>
        </div>
      </div>

      <div class="prompt-meta">
        <span>Phases: {deliverable.claudeCodePrompt.phases}</span>
        <span>Est. Time: {deliverable.claudeCodePrompt.estimatedTime}</span>
      </div>
      
      <pre class="content-body">{deliverable.claudeCodePrompt.content}</pre>
    {/if}
  </div>
</div>

<style>
  .final-plan-viewer {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .viewer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid var(--border-primary);
  }

  .viewer-header h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--border-primary);
  }

  .tab {
    flex: 1;
    padding: 0.75rem;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-secondary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .tab:hover {
    color: var(--text-primary);
  }

  .tab.active {
    color: var(--ember-400);
    border-bottom-color: var(--ember-400);
  }

  .content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .content-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--surface-secondary);
    border-bottom: 1px solid var(--border-primary);
  }

  .filename {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .content-actions {
    display: flex;
    gap: 0.5rem;
  }

  .sections-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--surface-tertiary);
    border-bottom: 1px solid var(--border-primary);
  }

  .section-link {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    padding: 0.25rem 0.5rem;
    background: var(--surface-secondary);
    border-radius: 0.25rem;
  }

  .prompt-meta {
    display: flex;
    gap: 1.5rem;
    padding: 0.75rem 1rem;
    background: var(--surface-tertiary);
    border-bottom: 1px solid var(--border-primary);
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .content-body {
    flex: 1;
    margin: 0;
    padding: 1rem;
    overflow-y: auto;
    font-size: 0.8125rem;
    line-height: 1.6;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
```

---

## Task 7: Create Barrel Export

Create `src/lib/workbench/planning/index.ts`:

```typescript
// Types
export * from './types';

// Store
export { planningStore } from './stores/planning.svelte';

// Services
export { modelRouter } from './services/modelRouter';
export { planningOrchestrator } from './services/orchestrator';
export { deliverableParser } from './services/parser';

// Components
export { default as PlanningPanel } from './components/PlanningPanel.svelte';
export { default as PlanningStages } from './components/PlanningStages.svelte';
export { default as StageCard } from './components/StageCard.svelte';
export { default as RequestInput } from './components/RequestInput.svelte';
export { default as PlanningControls } from './components/PlanningControls.svelte';
export { default as FinalPlanViewer } from './components/FinalPlanViewer.svelte';
```

---

## Task 8: Verify and Checkpoint

```bash
pnpm check
pnpm test

git add -A
git commit -m "feat(planning): Add Planning UI components for Cortex Multi-AI Orchestrator"
git tag step-6-ui-complete
```

**GATE:** All tests pass, components render without errors. Do not proceed until gate passes.
```

---

# Summary: Steps 1-6 Complete

After completing Steps 1-6, you'll have:

| Component | Files Created |
|-----------|---------------|
| **License System** | Types, Store, FeatureGate, UpgradePrompt, TrialBanner |
| **Planning Types** | Complete type definitions for Cortex |
| **Model Router** | Multi-provider AI routing service |
| **Orchestrator** | 4-stage workflow execution engine |
| **Planning Store** | Session state management |
| **Planning UI** | Full UI for the Multi-AI Orchestrator |

**Total estimated time:** ~12 hours (Claude Code)

**Git tags created:**
- `step-1-license-complete`
- `step-2-types-complete`
- `step-3-router-complete`
- `step-4-orchestrator-complete`
- `step-5-store-complete`
- `step-6-ui-complete`

Continue to Steps 7-9 for Model Comparison, Integration, and Testing.
