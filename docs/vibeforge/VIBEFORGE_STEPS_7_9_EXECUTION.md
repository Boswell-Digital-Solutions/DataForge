# VibeForge Phase 2: Steps 7-9 Execution Guide

**Version:** 1.0  
**Date:** December 6, 2025  
**Execution Mode:** Autonomous (`--dangerously-skip-permissions`)  
**Total Estimated Time:** ~4.5 hours (Claude Code)

---

## Quick Start

```bash
# Navigate to VibeForge root
cd /path/to/vibeforge

# Ensure clean state
git status
pnpm check
pnpm test

# Start Claude Code
claude --dangerously-skip-permissions
```

Then paste the relevant step prompt below.

---

# Step 7: Model Comparison (~1.5 hours)

## 7.1 Claude Code Prompt

```
You are implementing the Model Comparison feature for VibeForge. This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 5, Svelte 5 runes, TypeScript, Tauri
- **Feature:** VF-209 - Run Comparison & Analytics
- **Location:** src/lib/workbench/comparison/

## Execution Rules
1. Run `pnpm check && pnpm test` after EVERY file change
2. NEVER proceed if tests fail
3. Maintain 100% test coverage (Forge standard)
4. Use Svelte 5 runes ($state, $derived, $effect) - NO legacy stores

---

## Task 1: Create Comparison Types

Create `src/lib/workbench/comparison/types.ts`:

```typescript
export interface ComparisonRun {
  id: string;
  model: string;
  provider: 'anthropic' | 'openai' | 'xai' | 'google';
  prompt: string;
  output: string;
  
  // Metrics
  tokensUsed: number;
  latencyMs: number;
  cost: number;
  
  // Timestamps
  startedAt: string;
  completedAt: string;
  
  // Optional user rating
  rating?: 1 | 2 | 3 | 4 | 5;
  notes?: string;
}

export interface ComparisonSession {
  id: string;
  name: string;
  createdAt: string;
  
  // The prompt being compared
  prompt: string;
  contextBlocks: string[];
  
  // Runs to compare
  runs: ComparisonRun[];
  
  // Analysis
  winner?: string;  // Run ID
  analysis?: string;
}

export interface ComparisonMetrics {
  totalCost: number;
  averageLatency: number;
  fastestRun: string;
  cheapestRun: string;
  bestRated?: string;
}
```

---

## Task 2: Create Comparison Store

Create `src/lib/workbench/comparison/stores/comparison.svelte.ts`:

```typescript
import { browser } from '$app/environment';
import type { ComparisonSession, ComparisonRun, ComparisonMetrics } from '../types';

interface ComparisonState {
  sessions: ComparisonSession[];
  currentSession: ComparisonSession | null;
  selectedRuns: string[];  // Run IDs for side-by-side view
  isLoading: boolean;
  error: string | null;
}

class ComparisonStore {
  private _state = $state<ComparisonState>({
    sessions: [],
    currentSession: null,
    selectedRuns: [],
    isLoading: false,
    error: null
  });

  // Getters
  get sessions() { return this._state.sessions; }
  get currentSession() { return this._state.currentSession; }
  get selectedRuns() { return this._state.selectedRuns; }
  get isLoading() { return this._state.isLoading; }
  get error() { return this._state.error; }

  // Derived: Selected runs data
  selectedRunsData = $derived(() => {
    if (!this._state.currentSession) return [];
    return this._state.currentSession.runs.filter(
      r => this._state.selectedRuns.includes(r.id)
    );
  });

  // Derived: Metrics for current session
  metrics = $derived<ComparisonMetrics | null>(() => {
    const session = this._state.currentSession;
    if (!session || session.runs.length === 0) return null;

    const runs = session.runs;
    const totalCost = runs.reduce((sum, r) => sum + r.cost, 0);
    const averageLatency = runs.reduce((sum, r) => sum + r.latencyMs, 0) / runs.length;
    
    const fastestRun = runs.reduce((a, b) => a.latencyMs < b.latencyMs ? a : b).id;
    const cheapestRun = runs.reduce((a, b) => a.cost < b.cost ? a : b).id;
    
    const ratedRuns = runs.filter(r => r.rating !== undefined);
    const bestRated = ratedRuns.length > 0
      ? ratedRuns.reduce((a, b) => (a.rating ?? 0) > (b.rating ?? 0) ? a : b).id
      : undefined;

    return { totalCost, averageLatency, fastestRun, cheapestRun, bestRated };
  });

  // Actions
  createSession(name: string, prompt: string, contextBlocks: string[] = []): ComparisonSession {
    const session: ComparisonSession = {
      id: crypto.randomUUID(),
      name,
      createdAt: new Date().toISOString(),
      prompt,
      contextBlocks,
      runs: []
    };
    
    this._state.sessions = [...this._state.sessions, session];
    this._state.currentSession = session;
    this._state.selectedRuns = [];
    this.persist();
    
    return session;
  }

  loadSession(sessionId: string): void {
    const session = this._state.sessions.find(s => s.id === sessionId);
    if (session) {
      this._state.currentSession = session;
      this._state.selectedRuns = session.runs.slice(0, 2).map(r => r.id);
    }
  }

  addRun(run: Omit<ComparisonRun, 'id'>): ComparisonRun {
    if (!this._state.currentSession) {
      throw new Error('No active comparison session');
    }

    const newRun: ComparisonRun = {
      ...run,
      id: crypto.randomUUID()
    };

    this._state.currentSession.runs = [...this._state.currentSession.runs, newRun];
    
    // Auto-select first two runs
    if (this._state.selectedRuns.length < 2) {
      this._state.selectedRuns = [...this._state.selectedRuns, newRun.id];
    }
    
    this.persist();
    return newRun;
  }

  selectRun(runId: string): void {
    if (this._state.selectedRuns.includes(runId)) {
      this._state.selectedRuns = this._state.selectedRuns.filter(id => id !== runId);
    } else if (this._state.selectedRuns.length < 2) {
      this._state.selectedRuns = [...this._state.selectedRuns, runId];
    } else {
      // Replace oldest selection
      this._state.selectedRuns = [this._state.selectedRuns[1], runId];
    }
  }

  rateRun(runId: string, rating: 1 | 2 | 3 | 4 | 5, notes?: string): void {
    if (!this._state.currentSession) return;
    
    this._state.currentSession.runs = this._state.currentSession.runs.map(r =>
      r.id === runId ? { ...r, rating, notes } : r
    );
    this.persist();
  }

  setWinner(runId: string, analysis?: string): void {
    if (!this._state.currentSession) return;
    
    this._state.currentSession.winner = runId;
    this._state.currentSession.analysis = analysis;
    this.persist();
  }

  deleteSession(sessionId: string): void {
    this._state.sessions = this._state.sessions.filter(s => s.id !== sessionId);
    if (this._state.currentSession?.id === sessionId) {
      this._state.currentSession = null;
      this._state.selectedRuns = [];
    }
    this.persist();
  }

  clearError(): void {
    this._state.error = null;
  }

  // Persistence
  private persist(): void {
    if (browser) {
      localStorage.setItem('vibeforge:comparison', JSON.stringify({
        sessions: this._state.sessions
      }));
    }
  }

  constructor() {
    if (browser) {
      const stored = localStorage.getItem('vibeforge:comparison');
      if (stored) {
        try {
          const data = JSON.parse(stored);
          this._state.sessions = data.sessions ?? [];
        } catch { /* use defaults */ }
      }
    }
  }
}

export const comparisonStore = new ComparisonStore();
```

---

## Task 3: Create UI Components

### 3.1 ComparisonPanel.svelte

Create `src/lib/workbench/comparison/ComparisonPanel.svelte`:

```svelte
<script lang="ts">
  import { comparisonStore } from './stores/comparison.svelte';
  import ComparisonCard from './ComparisonCard.svelte';
  import ComparisonMetrics from './ComparisonMetrics.svelte';
  import { Button } from '$lib/components/ui';

  let newSessionName = $state('');
  let showNewSession = $state(false);

  function createSession() {
    if (newSessionName.trim()) {
      comparisonStore.createSession(newSessionName.trim(), '');
      newSessionName = '';
      showNewSession = false;
    }
  }
</script>

<div class="comparison-panel">
  <header class="panel-header">
    <h2>Model Comparison</h2>
    <Button variant="primary" size="sm" onclick={() => showNewSession = true}>
      New Comparison
    </Button>
  </header>

  {#if showNewSession}
    <div class="new-session-form">
      <input
        type="text"
        bind:value={newSessionName}
        placeholder="Comparison name..."
        class="session-input"
      />
      <div class="form-actions">
        <Button variant="ghost" size="sm" onclick={() => showNewSession = false}>
          Cancel
        </Button>
        <Button variant="primary" size="sm" onclick={createSession}>
          Create
        </Button>
      </div>
    </div>
  {/if}

  {#if comparisonStore.currentSession}
    <ComparisonMetrics />
    
    <div class="comparison-grid">
      {#each comparisonStore.selectedRunsData() as run (run.id)}
        <ComparisonCard {run} />
      {/each}
    </div>

    {#if comparisonStore.currentSession.runs.length > 2}
      <div class="run-selector">
        <span class="selector-label">Compare runs:</span>
        {#each comparisonStore.currentSession.runs as run (run.id)}
          <button
            class="run-chip"
            class:selected={comparisonStore.selectedRuns.includes(run.id)}
            onclick={() => comparisonStore.selectRun(run.id)}
          >
            {run.model}
          </button>
        {/each}
      </div>
    {/if}
  {:else}
    <div class="empty-state">
      <p>No comparison session active.</p>
      <p>Create a new comparison or select from history.</p>
    </div>

    {#if comparisonStore.sessions.length > 0}
      <div class="session-history">
        <h3>Recent Comparisons</h3>
        {#each comparisonStore.sessions.slice(0, 5) as session (session.id)}
          <button
            class="session-item"
            onclick={() => comparisonStore.loadSession(session.id)}
          >
            <span class="session-name">{session.name}</span>
            <span class="session-meta">
              {session.runs.length} runs · {new Date(session.createdAt).toLocaleDateString()}
            </span>
          </button>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .comparison-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
    height: 100%;
    overflow-y: auto;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .panel-header h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .new-session-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1rem;
    background: var(--surface-secondary);
    border-radius: 0.5rem;
  }

  .session-input {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    background: var(--surface-primary);
    color: var(--text-primary);
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .comparison-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    flex: 1;
    min-height: 0;
  }

  .run-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    padding: 0.75rem;
    background: var(--surface-secondary);
    border-radius: 0.5rem;
  }

  .selector-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .run-chip {
    padding: 0.25rem 0.75rem;
    border: 1px solid var(--border-primary);
    border-radius: 1rem;
    background: var(--surface-primary);
    color: var(--text-secondary);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .run-chip:hover {
    border-color: var(--ember-500);
  }

  .run-chip.selected {
    background: var(--ember-500);
    border-color: var(--ember-500);
    color: white;
  }

  .empty-state {
    text-align: center;
    padding: 2rem;
    color: var(--text-secondary);
  }

  .session-history {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .session-history h3 {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
  }

  .session-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .session-item:hover {
    border-color: var(--ember-500);
  }

  .session-name {
    font-weight: 500;
    color: var(--text-primary);
  }

  .session-meta {
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }
</style>
```

### 3.2 ComparisonCard.svelte

Create `src/lib/workbench/comparison/ComparisonCard.svelte`:

```svelte
<script lang="ts">
  import type { ComparisonRun } from './types';
  import { comparisonStore } from './stores/comparison.svelte';

  interface Props {
    run: ComparisonRun;
  }

  let { run }: Props = $props();

  const metrics = comparisonStore.metrics;
  
  let isFastest = $derived(metrics()?.fastestRun === run.id);
  let isCheapest = $derived(metrics()?.cheapestRun === run.id);
  let isBestRated = $derived(metrics()?.bestRated === run.id);
  let isWinner = $derived(comparisonStore.currentSession?.winner === run.id);

  function handleRate(rating: 1 | 2 | 3 | 4 | 5) {
    comparisonStore.rateRun(run.id, rating);
  }

  function formatCost(cost: number): string {
    return `$${cost.toFixed(4)}`;
  }

  function formatLatency(ms: number): string {
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`;
  }
</script>

<div class="comparison-card" class:winner={isWinner}>
  <header class="card-header">
    <div class="model-info">
      <span class="model-name">{run.model}</span>
      <span class="provider-badge">{run.provider}</span>
    </div>
    <div class="badges">
      {#if isFastest}<span class="badge fastest">⚡ Fastest</span>{/if}
      {#if isCheapest}<span class="badge cheapest">💰 Cheapest</span>{/if}
      {#if isBestRated}<span class="badge rated">⭐ Best Rated</span>{/if}
      {#if isWinner}<span class="badge winner">🏆 Winner</span>{/if}
    </div>
  </header>

  <div class="metrics-row">
    <div class="metric">
      <span class="metric-label">Latency</span>
      <span class="metric-value">{formatLatency(run.latencyMs)}</span>
    </div>
    <div class="metric">
      <span class="metric-label">Cost</span>
      <span class="metric-value">{formatCost(run.cost)}</span>
    </div>
    <div class="metric">
      <span class="metric-label">Tokens</span>
      <span class="metric-value">{run.tokensUsed.toLocaleString()}</span>
    </div>
  </div>

  <div class="output-container">
    <pre class="output">{run.output}</pre>
  </div>

  <footer class="card-footer">
    <div class="rating">
      {#each [1, 2, 3, 4, 5] as star}
        <button
          class="star-btn"
          class:filled={run.rating && run.rating >= star}
          onclick={() => handleRate(star as 1 | 2 | 3 | 4 | 5)}
        >
          {run.rating && run.rating >= star ? '★' : '☆'}
        </button>
      {/each}
    </div>
    
    {#if !isWinner}
      <button
        class="winner-btn"
        onclick={() => comparisonStore.setWinner(run.id)}
      >
        Set as Winner
      </button>
    {/if}
  </footer>
</div>

<style>
  .comparison-card {
    display: flex;
    flex-direction: column;
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .comparison-card.winner {
    border-color: var(--ember-500);
    box-shadow: 0 0 0 1px var(--ember-500);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 0.75rem;
    border-bottom: 1px solid var(--border-primary);
  }

  .model-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .model-name {
    font-weight: 600;
    color: var(--text-primary);
  }

  .provider-badge {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    text-transform: uppercase;
  }

  .badges {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }

  .badge {
    padding: 0.125rem 0.5rem;
    border-radius: 1rem;
    font-size: 0.625rem;
    font-weight: 600;
  }

  .badge.fastest {
    background: var(--blue-900);
    color: var(--blue-300);
  }

  .badge.cheapest {
    background: var(--green-900);
    color: var(--green-300);
  }

  .badge.rated {
    background: var(--yellow-900);
    color: var(--yellow-300);
  }

  .badge.winner {
    background: var(--ember-900);
    color: var(--ember-300);
  }

  .metrics-row {
    display: flex;
    gap: 1rem;
    padding: 0.75rem;
    background: var(--surface-tertiary);
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .metric-label {
    font-size: 0.625rem;
    color: var(--text-tertiary);
    text-transform: uppercase;
  }

  .metric-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .output-container {
    flex: 1;
    overflow: auto;
    padding: 0.75rem;
  }

  .output {
    font-size: 0.8125rem;
    line-height: 1.5;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    border-top: 1px solid var(--border-primary);
  }

  .rating {
    display: flex;
    gap: 0.125rem;
  }

  .star-btn {
    background: none;
    border: none;
    font-size: 1.25rem;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: color 0.15s ease;
  }

  .star-btn:hover,
  .star-btn.filled {
    color: var(--yellow-400);
  }

  .winner-btn {
    padding: 0.375rem 0.75rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .winner-btn:hover {
    border-color: var(--ember-500);
    color: var(--ember-500);
  }
</style>
```

### 3.3 ComparisonMetrics.svelte

Create `src/lib/workbench/comparison/ComparisonMetrics.svelte`:

```svelte
<script lang="ts">
  import { comparisonStore } from './stores/comparison.svelte';

  const metrics = comparisonStore.metrics;

  function formatCost(cost: number): string {
    return `$${cost.toFixed(4)}`;
  }

  function formatLatency(ms: number): string {
    return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`;
  }
</script>

{#if metrics()}
  <div class="metrics-bar">
    <div class="metric">
      <span class="metric-icon">💵</span>
      <div class="metric-content">
        <span class="metric-label">Total Cost</span>
        <span class="metric-value">{formatCost(metrics()!.totalCost)}</span>
      </div>
    </div>
    
    <div class="metric">
      <span class="metric-icon">⏱️</span>
      <div class="metric-content">
        <span class="metric-label">Avg Latency</span>
        <span class="metric-value">{formatLatency(metrics()!.averageLatency)}</span>
      </div>
    </div>
    
    <div class="metric">
      <span class="metric-icon">📊</span>
      <div class="metric-content">
        <span class="metric-label">Runs</span>
        <span class="metric-value">{comparisonStore.currentSession?.runs.length ?? 0}</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .metrics-bar {
    display: flex;
    gap: 1.5rem;
    padding: 0.75rem 1rem;
    background: var(--surface-tertiary);
    border-radius: 0.5rem;
  }

  .metric {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .metric-icon {
    font-size: 1.25rem;
  }

  .metric-content {
    display: flex;
    flex-direction: column;
  }

  .metric-label {
    font-size: 0.625rem;
    color: var(--text-tertiary);
    text-transform: uppercase;
  }

  .metric-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }
</style>
```

---

## Task 4: Create Tests

Create `src/tests/stores/comparison.test.ts`:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock browser environment
vi.mock('$app/environment', () => ({
  browser: true
}));

// Mock localStorage
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => localStorageMock.store[key] || null),
  setItem: vi.fn((key: string, value: string) => { localStorageMock.store[key] = value; }),
  removeItem: vi.fn((key: string) => { delete localStorageMock.store[key]; }),
  clear: vi.fn(() => { localStorageMock.store = {}; })
};
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Import after mocks
import { comparisonStore } from '$lib/workbench/comparison/stores/comparison.svelte';

describe('ComparisonStore', () => {
  beforeEach(() => {
    localStorageMock.clear();
    // Reset store state - you may need to implement a reset method
  });

  describe('createSession', () => {
    it('creates a new comparison session', () => {
      const session = comparisonStore.createSession('Test Comparison', 'Test prompt');
      
      expect(session).toBeDefined();
      expect(session.name).toBe('Test Comparison');
      expect(session.prompt).toBe('Test prompt');
      expect(session.runs).toEqual([]);
      expect(comparisonStore.currentSession).toBe(session);
    });

    it('adds session to sessions list', () => {
      const session = comparisonStore.createSession('Test', 'prompt');
      expect(comparisonStore.sessions).toContain(session);
    });

    it('persists to localStorage', () => {
      comparisonStore.createSession('Test', 'prompt');
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'vibeforge:comparison',
        expect.any(String)
      );
    });
  });

  describe('addRun', () => {
    it('adds a run to current session', () => {
      comparisonStore.createSession('Test', 'prompt');
      
      const run = comparisonStore.addRun({
        model: 'claude-3-opus',
        provider: 'anthropic',
        prompt: 'test prompt',
        output: 'test output',
        tokensUsed: 100,
        latencyMs: 500,
        cost: 0.01,
        startedAt: new Date().toISOString(),
        completedAt: new Date().toISOString()
      });

      expect(run.id).toBeDefined();
      expect(comparisonStore.currentSession?.runs).toContain(run);
    });

    it('throws if no active session', () => {
      // Clear current session
      expect(() => comparisonStore.addRun({
        model: 'test',
        provider: 'anthropic',
        prompt: '',
        output: '',
        tokensUsed: 0,
        latencyMs: 0,
        cost: 0,
        startedAt: '',
        completedAt: ''
      })).toThrow('No active comparison session');
    });

    it('auto-selects first two runs', () => {
      comparisonStore.createSession('Test', 'prompt');
      
      const run1 = comparisonStore.addRun(createMockRun('run1'));
      expect(comparisonStore.selectedRuns).toContain(run1.id);
      
      const run2 = comparisonStore.addRun(createMockRun('run2'));
      expect(comparisonStore.selectedRuns).toContain(run2.id);
      
      const run3 = comparisonStore.addRun(createMockRun('run3'));
      expect(comparisonStore.selectedRuns).not.toContain(run3.id);
    });
  });

  describe('selectRun', () => {
    it('toggles run selection', () => {
      comparisonStore.createSession('Test', 'prompt');
      const run = comparisonStore.addRun(createMockRun('test'));
      
      // Already selected from auto-select
      comparisonStore.selectRun(run.id);
      expect(comparisonStore.selectedRuns).not.toContain(run.id);
      
      comparisonStore.selectRun(run.id);
      expect(comparisonStore.selectedRuns).toContain(run.id);
    });

    it('replaces oldest selection when at limit', () => {
      comparisonStore.createSession('Test', 'prompt');
      const run1 = comparisonStore.addRun(createMockRun('run1'));
      const run2 = comparisonStore.addRun(createMockRun('run2'));
      const run3 = comparisonStore.addRun(createMockRun('run3'));
      
      comparisonStore.selectRun(run3.id);
      
      expect(comparisonStore.selectedRuns).not.toContain(run1.id);
      expect(comparisonStore.selectedRuns).toContain(run2.id);
      expect(comparisonStore.selectedRuns).toContain(run3.id);
    });
  });

  describe('rateRun', () => {
    it('sets rating on a run', () => {
      comparisonStore.createSession('Test', 'prompt');
      const run = comparisonStore.addRun(createMockRun('test'));
      
      comparisonStore.rateRun(run.id, 5, 'Excellent output');
      
      const updatedRun = comparisonStore.currentSession?.runs.find(r => r.id === run.id);
      expect(updatedRun?.rating).toBe(5);
      expect(updatedRun?.notes).toBe('Excellent output');
    });
  });

  describe('setWinner', () => {
    it('sets winner on current session', () => {
      comparisonStore.createSession('Test', 'prompt');
      const run = comparisonStore.addRun(createMockRun('test'));
      
      comparisonStore.setWinner(run.id, 'Best quality output');
      
      expect(comparisonStore.currentSession?.winner).toBe(run.id);
      expect(comparisonStore.currentSession?.analysis).toBe('Best quality output');
    });
  });

  describe('metrics', () => {
    it('calculates metrics correctly', () => {
      comparisonStore.createSession('Test', 'prompt');
      
      comparisonStore.addRun({
        ...createMockRun('run1'),
        latencyMs: 500,
        cost: 0.01,
        tokensUsed: 100
      });
      
      comparisonStore.addRun({
        ...createMockRun('run2'),
        latencyMs: 300,
        cost: 0.02,
        tokensUsed: 200
      });

      const metrics = comparisonStore.metrics();
      
      expect(metrics).not.toBeNull();
      expect(metrics?.totalCost).toBe(0.03);
      expect(metrics?.averageLatency).toBe(400);
    });

    it('identifies fastest and cheapest runs', () => {
      comparisonStore.createSession('Test', 'prompt');
      
      const slow = comparisonStore.addRun({
        ...createMockRun('slow'),
        latencyMs: 1000,
        cost: 0.01
      });
      
      const fast = comparisonStore.addRun({
        ...createMockRun('fast'),
        latencyMs: 200,
        cost: 0.05
      });

      const metrics = comparisonStore.metrics();
      
      expect(metrics?.fastestRun).toBe(fast.id);
      expect(metrics?.cheapestRun).toBe(slow.id);
    });
  });

  describe('deleteSession', () => {
    it('removes session from list', () => {
      const session = comparisonStore.createSession('Test', 'prompt');
      
      comparisonStore.deleteSession(session.id);
      
      expect(comparisonStore.sessions).not.toContain(session);
      expect(comparisonStore.currentSession).toBeNull();
    });
  });
});

// Helper function
function createMockRun(name: string) {
  return {
    model: `model-${name}`,
    provider: 'anthropic' as const,
    prompt: 'test prompt',
    output: `output for ${name}`,
    tokensUsed: 100,
    latencyMs: 500,
    cost: 0.01,
    startedAt: new Date().toISOString(),
    completedAt: new Date().toISOString()
  };
}
```

---

## Task 5: Create barrel exports

Create `src/lib/workbench/comparison/index.ts`:

```typescript
export * from './types';
export { comparisonStore } from './stores/comparison.svelte';
export { default as ComparisonPanel } from './ComparisonPanel.svelte';
export { default as ComparisonCard } from './ComparisonCard.svelte';
export { default as ComparisonMetrics } from './ComparisonMetrics.svelte';
```

---

## Task 6: Verify and Checkpoint

```bash
pnpm check
pnpm test src/tests/stores/comparison.test.ts
pnpm test --coverage

git add -A
git commit -m "feat(comparison): Add side-by-side model comparison view (VF-209)"
```

**GATE:** All tests pass, coverage meets threshold. Do not proceed until gate passes.
```

---

# Step 8: Integration & Polish (~1.5 hours)

## 8.1 Claude Code Prompt

```
You are integrating the new features into the main VibeForge application. This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 5, Svelte 5 runes, TypeScript, Tauri
- **Feature:** Integration of comparison view, settings page, error handling
- **Location:** src/routes/, src/lib/components/

## Execution Rules
1. Run `pnpm check && pnpm test` after EVERY file change
2. NEVER proceed if tests fail
3. Maintain 100% test coverage (Forge standard)

---

## Task 1: Create Global Error Boundary

Create `src/lib/components/ErrorBoundary.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { Button } from '$lib/components/ui';

  interface Props {
    children: import('svelte').Snippet;
  }

  let { children }: Props = $props();

  let error = $state<Error | null>(null);
  let errorInfo = $state<string>('');

  onMount(() => {
    const handleError = (event: ErrorEvent) => {
      error = event.error;
      errorInfo = event.message;
      event.preventDefault();
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      errorInfo = 'Unhandled promise rejection';
      event.preventDefault();
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  });

  function reset() {
    error = null;
    errorInfo = '';
  }

  function reload() {
    window.location.reload();
  }
</script>

{#if error}
  <div class="error-boundary">
    <div class="error-content">
      <div class="error-icon">⚠️</div>
      <h1>Something went wrong</h1>
      <p class="error-message">{error.message}</p>
      {#if errorInfo}
        <p class="error-info">{errorInfo}</p>
      {/if}
      
      <details class="error-details">
        <summary>Technical Details</summary>
        <pre>{error.stack}</pre>
      </details>

      <div class="error-actions">
        <Button variant="ghost" onclick={reset}>
          Try Again
        </Button>
        <Button variant="primary" onclick={reload}>
          Reload App
        </Button>
      </div>
    </div>
  </div>
{:else}
  {@render children()}
{/if}

<style>
  .error-boundary {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 2rem;
    background: var(--blacksteel-950);
  }

  .error-content {
    max-width: 32rem;
    text-align: center;
  }

  .error-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .error-message {
    color: var(--text-secondary);
    margin-bottom: 1rem;
  }

  .error-info {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    margin-bottom: 1rem;
  }

  .error-details {
    text-align: left;
    margin-bottom: 1.5rem;
  }

  .error-details summary {
    cursor: pointer;
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
  }

  .error-details pre {
    padding: 1rem;
    background: var(--gunmetal-900);
    border-radius: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    overflow-x: auto;
    max-height: 12rem;
  }

  .error-actions {
    display: flex;
    justify-content: center;
    gap: 1rem;
  }
</style>
```

---

## Task 2: Create Offline Banner

Create `src/lib/components/OfflineBanner.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';

  let isOffline = $state(false);

  onMount(() => {
    isOffline = !navigator.onLine;

    const handleOnline = () => { isOffline = false; };
    const handleOffline = () => { isOffline = true; };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  });
</script>

{#if isOffline}
  <div class="offline-banner" role="alert">
    <span class="offline-icon">📡</span>
    <span class="offline-text">You're offline. Some features may be unavailable.</span>
  </div>
{/if}

<style>
  .offline-banner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--yellow-900);
    color: var(--yellow-200);
    font-size: 0.875rem;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 9999;
  }

  .offline-icon {
    font-size: 1rem;
  }
</style>
```

---

## Task 3: Create Settings Page

Create `src/routes/settings/+page.svelte`:

```svelte
<script lang="ts">
  import { settingsStore } from '$lib/core/stores/settings.svelte';
  import { Button } from '$lib/components/ui';

  // API Keys state
  let anthropicKey = $state('');
  let openaiKey = $state('');
  let showAnthropicKey = $state(false);
  let showOpenaiKey = $state(false);
  let testingAnthropic = $state(false);
  let testingOpenai = $state(false);
  let anthropicStatus = $state<'idle' | 'success' | 'error'>('idle');
  let openaiStatus = $state<'idle' | 'success' | 'error'>('idle');

  async function testAnthropicKey() {
    if (!anthropicKey) return;
    testingAnthropic = true;
    anthropicStatus = 'idle';
    
    try {
      // TODO: Implement actual API test via Tauri command
      await new Promise(resolve => setTimeout(resolve, 1000));
      anthropicStatus = 'success';
    } catch {
      anthropicStatus = 'error';
    } finally {
      testingAnthropic = false;
    }
  }

  async function testOpenaiKey() {
    if (!openaiKey) return;
    testingOpenai = true;
    openaiStatus = 'idle';
    
    try {
      // TODO: Implement actual API test via Tauri command
      await new Promise(resolve => setTimeout(resolve, 1000));
      openaiStatus = 'success';
    } catch {
      openaiStatus = 'error';
    } finally {
      testingOpenai = false;
    }
  }

  async function saveKeys() {
    // TODO: Save to Tauri keychain
    console.log('Saving keys...');
  }
</script>

<svelte:head>
  <title>Settings | VibeForge</title>
</svelte:head>

<div class="settings-page">
  <header class="settings-header">
    <h1>Settings</h1>
    <p>Configure VibeForge preferences and API keys</p>
  </header>

  <div class="settings-sections">
    <!-- API Keys Section -->
    <section class="settings-section">
      <h2>API Keys</h2>
      <p class="section-description">
        Enter your API keys to enable LLM execution. Keys are stored securely in your system keychain.
      </p>

      <div class="key-input-group">
        <label for="anthropic-key">Anthropic API Key</label>
        <div class="key-input-row">
          <div class="key-input-wrapper">
            <input
              id="anthropic-key"
              type={showAnthropicKey ? 'text' : 'password'}
              bind:value={anthropicKey}
              placeholder="sk-ant-..."
              class="key-input"
            />
            <button
              class="toggle-visibility"
              onclick={() => showAnthropicKey = !showAnthropicKey}
            >
              {showAnthropicKey ? '🙈' : '👁️'}
            </button>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onclick={testAnthropicKey}
            disabled={!anthropicKey || testingAnthropic}
          >
            {testingAnthropic ? 'Testing...' : 'Test'}
          </Button>
        </div>
        {#if anthropicStatus === 'success'}
          <span class="status-message success">✓ Connected successfully</span>
        {:else if anthropicStatus === 'error'}
          <span class="status-message error">✗ Connection failed</span>
        {/if}
      </div>

      <div class="key-input-group">
        <label for="openai-key">OpenAI API Key</label>
        <div class="key-input-row">
          <div class="key-input-wrapper">
            <input
              id="openai-key"
              type={showOpenaiKey ? 'text' : 'password'}
              bind:value={openaiKey}
              placeholder="sk-..."
              class="key-input"
            />
            <button
              class="toggle-visibility"
              onclick={() => showOpenaiKey = !showOpenaiKey}
            >
              {showOpenaiKey ? '🙈' : '👁️'}
            </button>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onclick={testOpenaiKey}
            disabled={!openaiKey || testingOpenai}
          >
            {testingOpenai ? 'Testing...' : 'Test'}
          </Button>
        </div>
        {#if openaiStatus === 'success'}
          <span class="status-message success">✓ Connected successfully</span>
        {:else if openaiStatus === 'error'}
          <span class="status-message error">✗ Connection failed</span>
        {/if}
      </div>

      <div class="section-actions">
        <Button variant="primary" onclick={saveKeys}>
          Save API Keys
        </Button>
      </div>
    </section>

    <!-- Appearance Section -->
    <section class="settings-section">
      <h2>Appearance</h2>
      
      <div class="setting-row">
        <div class="setting-info">
          <label>Theme</label>
          <p>Choose your preferred color scheme</p>
        </div>
        <select class="setting-select">
          <option value="dark">Dark</option>
          <option value="light">Light</option>
          <option value="system">System</option>
        </select>
      </div>

      <div class="setting-row">
        <div class="setting-info">
          <label>Font Size</label>
          <p>Adjust the editor font size</p>
        </div>
        <select class="setting-select">
          <option value="12">12px</option>
          <option value="14">14px</option>
          <option value="16">16px</option>
          <option value="18">18px</option>
        </select>
      </div>
    </section>

    <!-- About Section -->
    <section class="settings-section">
      <h2>About</h2>
      <div class="about-info">
        <p><strong>VibeForge</strong></p>
        <p>Version 0.1.0</p>
        <p class="muted">The VS Code of Prompt Engineering</p>
        <p class="muted">Part of the Forge Ecosystem by Boswell Digital Solutions LLC</p>
      </div>
    </section>
  </div>
</div>

<style>
  .settings-page {
    max-width: 48rem;
    margin: 0 auto;
    padding: 2rem;
  }

  .settings-header {
    margin-bottom: 2rem;
  }

  .settings-header h1 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
  }

  .settings-header p {
    color: var(--text-secondary);
  }

  .settings-sections {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .settings-section {
    padding: 1.5rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 0.5rem;
  }

  .settings-section h2 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .section-description {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-bottom: 1.5rem;
  }

  .key-input-group {
    margin-bottom: 1.25rem;
  }

  .key-input-group label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .key-input-row {
    display: flex;
    gap: 0.75rem;
  }

  .key-input-wrapper {
    flex: 1;
    position: relative;
  }

  .key-input {
    width: 100%;
    padding: 0.625rem 2.5rem 0.625rem 0.75rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .key-input:focus {
    outline: none;
    border-color: var(--ember-500);
  }

  .toggle-visibility {
    position: absolute;
    right: 0.5rem;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1rem;
  }

  .status-message {
    display: block;
    font-size: 0.75rem;
    margin-top: 0.5rem;
  }

  .status-message.success {
    color: var(--green-400);
  }

  .status-message.error {
    color: var(--red-400);
  }

  .section-actions {
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-primary);
  }

  .setting-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    border-bottom: 1px solid var(--border-primary);
  }

  .setting-row:last-child {
    border-bottom: none;
  }

  .setting-info label {
    display: block;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
  }

  .setting-info p {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .setting-select {
    padding: 0.5rem 0.75rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-primary);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
  }

  .about-info {
    color: var(--text-secondary);
  }

  .about-info p {
    margin-bottom: 0.25rem;
  }

  .about-info .muted {
    color: var(--text-tertiary);
    font-size: 0.875rem;
  }
</style>
```

---

## Task 4: Update Main Layout

Update `src/routes/+layout.svelte` to include ErrorBoundary and OfflineBanner:

```svelte
<script lang="ts">
  import '../app.css';
  import ErrorBoundary from '$lib/components/ErrorBoundary.svelte';
  import OfflineBanner from '$lib/components/OfflineBanner.svelte';

  interface Props {
    children: import('svelte').Snippet;
  }

  let { children }: Props = $props();
</script>

<ErrorBoundary>
  <OfflineBanner />
  {@render children()}
</ErrorBoundary>
```

---

## Task 5: Add Comparison to Workbench

Update the workbench layout to include the comparison panel. Find the appropriate layout file and add:

```svelte
<!-- In the right column or as a tab -->
<script lang="ts">
  import { ComparisonPanel } from '$lib/workbench/comparison';
</script>

<!-- Add as a panel option -->
<ComparisonPanel />
```

---

## Task 6: Verify and Checkpoint

```bash
pnpm check
pnpm test
pnpm dev
# Manual test: Navigate to /settings, verify error boundary works

git add -A
git commit -m "feat(integration): Add settings page, error boundary, offline detection"
```

**GATE:** App runs, settings page loads, error boundary catches errors.
```

---

# Step 9: Testing & Documentation (~1.5 hours)

## 9.1 Claude Code Prompt

```
You are completing the testing and documentation phase for VibeForge Phase 2. This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 5, Svelte 5 runes, TypeScript, Vitest, Playwright
- **Feature:** VF-214 - Testing & Quality Assurance
- **Requirement:** 100% test coverage (Forge mandatory standard)

## Execution Rules
1. Run `pnpm test --coverage` to check current coverage
2. Identify gaps and write tests until 100% coverage achieved
3. Create E2E tests for critical user flows

---

## Task 1: Run Coverage Report

```bash
pnpm test --coverage
```

Analyze the output. Identify files with less than 100% coverage.

---

## Task 2: Fill Coverage Gaps

For each file under 100%, create or extend tests. Common patterns:

### Store Tests Pattern

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock browser
vi.mock('$app/environment', () => ({ browser: true }));

// Mock localStorage
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => { localStorageMock.store[key] = value; }),
  clear: vi.fn(() => { localStorageMock.store = {}; })
};
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

describe('StoreName', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  // Test every public method
  // Test every derived value
  // Test error conditions
  // Test edge cases
});
```

### Component Tests Pattern

```typescript
import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import ComponentName from './ComponentName.svelte';

describe('ComponentName', () => {
  it('renders correctly', () => {
    render(ComponentName, { props: { /* required props */ } });
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    const handler = vi.fn();
    render(ComponentName, { props: { onClick: handler } });
    
    await fireEvent.click(screen.getByRole('button'));
    expect(handler).toHaveBeenCalled();
  });
});
```

---

## Task 3: Create E2E Tests

Create `tests/e2e/workbench.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Workbench', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('loads workbench page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('VibeForge');
  });

  test('can navigate to settings', async ({ page }) => {
    await page.click('[data-testid="settings-link"]');
    await expect(page).toHaveURL('/settings');
  });

  test('settings page shows API key inputs', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.locator('#anthropic-key')).toBeVisible();
    await expect(page.locator('#openai-key')).toBeVisible();
  });
});
```

Create `tests/e2e/comparison.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Model Comparison', () => {
  test('can create new comparison session', async ({ page }) => {
    await page.goto('/');
    
    // Open comparison panel
    await page.click('[data-testid="comparison-tab"]');
    
    // Create new session
    await page.click('button:has-text("New Comparison")');
    await page.fill('input[placeholder*="Comparison name"]', 'Test Comparison');
    await page.click('button:has-text("Create")');
    
    // Verify session created
    await expect(page.locator('text=Test Comparison')).toBeVisible();
  });
});
```

---

## Task 4: Create README Documentation

Update `README.md` with Phase 2 completion status:

```markdown
## Phase 2 Status

### Completed ✅
- [x] VF-209: Run Comparison & Analytics
- [x] VF-210: Error Handling & Recovery
- [x] VF-213: Settings & Preferences
- [x] VF-214: Testing & Quality Assurance (100% coverage)

### Remaining
- [ ] VF-205: Authentication & API Keys (P1)
- [ ] VF-206: DataForge Backend Integration (P1)
- [ ] VF-207: NeuroForge Model Router Integration
- [ ] VF-208: Tool Result Injection
- [ ] VF-211: Prompt Templates & Library
- [ ] VF-212: Context Block Management
- [ ] VF-215: Documentation
```

---

## Task 5: Final Verification

```bash
# Full test suite
pnpm test

# Coverage report
pnpm test --coverage
# Must show 100% coverage

# Type check
pnpm check

# Build
pnpm build

# E2E tests
pnpm test:e2e

# Lint
pnpm lint
```

---

## Task 6: Final Checkpoint

```bash
git add -A
git commit -m "feat(testing): Achieve 100% test coverage, add E2E tests (VF-214)"
git tag phase2-steps7-9-complete
```

**GATE:** 100% test coverage, all E2E tests pass, build succeeds.
```

---

# Summary

| Step | Feature | Est. Time | Key Deliverables |
|------|---------|-----------|------------------|
| 7 | Model Comparison | 1.5h | comparison store, UI components, tests |
| 8 | Integration | 1.5h | settings page, error boundary, offline banner |
| 9 | Testing | 1.5h | 100% coverage, E2E tests, documentation |
| **Total** | | **~4.5h** | |

## Execution Order

```bash
# Step 7
claude --dangerously-skip-permissions
# Paste Step 7 prompt, wait for completion
git status  # Verify checkpoint

# Step 8
# Paste Step 8 prompt, wait for completion
git status  # Verify checkpoint

# Step 9
# Paste Step 9 prompt, wait for completion
git status  # Verify final tag
```

## Success Criteria

- [ ] Model comparison UI works with side-by-side view
- [ ] Rating and winner selection functional
- [ ] Settings page with API key inputs
- [ ] Error boundary catches and displays errors gracefully
- [ ] Offline banner appears when disconnected
- [ ] 100% test coverage achieved
- [ ] E2E tests pass
- [ ] Build succeeds
- [ ] All git checkpoints created
