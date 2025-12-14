# VibeForge Phase 2: Steps 1-4 Execution Guide

**Version:** 1.0  
**Date:** December 6, 2025  
**Execution Mode:** Autonomous (`--dangerously-skip-permissions`)  
**Total Estimated Time:** ~7.5 hours (Claude Code)

---

## Overview

| Step | Feature | Est. Time |
|------|---------|-----------|
| 1 | License Store & Feature Gates | ~1.5h |
| 2 | Planning Types & Data Models | ~1h |
| 3 | Model Router Service | ~2h |
| 4 | Planning Orchestrator | ~3h |

---

## Quick Start

```bash
cd /path/to/vibeforge
git status && pnpm check && pnpm test
claude --dangerously-skip-permissions
```

---

# Step 1: License Store & Feature Gates (~1.5 hours)

## 1.1 Claude Code Prompt

```
You are implementing the License Store and Feature Gates for VibeForge's freemium model. This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** SvelteKit 5, Svelte 5 runes, TypeScript, Tauri
- **Feature:** Freemium licensing with feature gating
- **Location:** src/lib/core/stores/, src/lib/components/

## Execution Rules
1. Run `pnpm check && pnpm test` after EVERY file change
2. NEVER proceed if tests fail
3. Maintain 100% test coverage (Forge standard)
4. Use Svelte 5 runes ($state, $derived, $effect) - NO legacy stores

---

## Task 1: Create License Types

Create `src/lib/core/types/license.ts`:

```typescript
export type LicenseTier = 'free' | 'trial' | 'pro' | 'enterprise';

export interface License {
  tier: LicenseTier;
  userId: string | null;
  email: string | null;
  expiresAt: Date | null;
  trialEndsAt: Date | null;
  features: Set<string>;
  limits: LicenseLimits;
  checkedAt: number;
}

export interface LicenseLimits {
  localHistoryMax: number;
  orchestratorRunsPerMonth: number;
  cloudHistoryMax: number;
  orchestratorUsedThisMonth: number;
}

export const FEATURES = {
  // Free tier
  WORKBENCH_BASIC: 'workbench.basic',
  EXECUTION_LOCAL: 'execution.local',
  WIZARD_ALL: 'wizard.all',
  SCAFFOLDING_ALL: 'scaffolding.all',
  ANALYSIS_BASIC: 'analysis.basic',
  HISTORY_LOCAL: 'history.local',
  
  // Pro/Trial tier
  ORCHESTRATOR_MULTI_AI: 'orchestrator.multiAI',
  EXECUTION_CLOUD: 'execution.cloud',
  HISTORY_CLOUD: 'history.cloud',
  ROUTING_SMART: 'routing.smart',
  LEARNING_RECOMMENDATIONS: 'learning.recommendations',
  COMPARISON_SIDE_BY_SIDE: 'comparison.sideBySide',
  WORKSPACES_TEAM: 'workspaces.team',
} as const;

export type FeatureFlag = typeof FEATURES[keyof typeof FEATURES];

export const DEFAULT_FREE_LICENSE: License = {
  tier: 'free',
  userId: null,
  email: null,
  expiresAt: null,
  trialEndsAt: null,
  features: new Set([
    FEATURES.WORKBENCH_BASIC,
    FEATURES.EXECUTION_LOCAL,
    FEATURES.WIZARD_ALL,
    FEATURES.SCAFFOLDING_ALL,
    FEATURES.ANALYSIS_BASIC,
    FEATURES.HISTORY_LOCAL,
  ]),
  limits: {
    localHistoryMax: 500,
    orchestratorRunsPerMonth: 0,
    cloudHistoryMax: 0,
    orchestratorUsedThisMonth: 0,
  },
  checkedAt: Date.now(),
};

export const DEFAULT_TRIAL_LICENSE: License = {
  tier: 'trial',
  userId: null,
  email: null,
  expiresAt: null,
  trialEndsAt: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
  features: new Set([
    ...DEFAULT_FREE_LICENSE.features,
    FEATURES.ORCHESTRATOR_MULTI_AI,
    FEATURES.EXECUTION_CLOUD,
    FEATURES.HISTORY_CLOUD,
    FEATURES.ROUTING_SMART,
    FEATURES.LEARNING_RECOMMENDATIONS,
    FEATURES.COMPARISON_SIDE_BY_SIDE,
  ]),
  limits: {
    localHistoryMax: 500,
    orchestratorRunsPerMonth: 20,
    cloudHistoryMax: 100,
    orchestratorUsedThisMonth: 0,
  },
  checkedAt: Date.now(),
};

export const DEFAULT_PRO_LICENSE: License = {
  tier: 'pro',
  userId: null,
  email: null,
  expiresAt: null,
  trialEndsAt: null,
  features: new Set([
    ...DEFAULT_TRIAL_LICENSE.features,
    FEATURES.WORKSPACES_TEAM,
  ]),
  limits: {
    localHistoryMax: Infinity,
    orchestratorRunsPerMonth: Infinity,
    cloudHistoryMax: Infinity,
    orchestratorUsedThisMonth: 0,
  },
  checkedAt: Date.now(),
};
```

---

## Task 2: Create License Store

Create `src/lib/core/stores/license.svelte.ts`:

```typescript
import { browser } from '$app/environment';
import type { License, LicenseTier, FeatureFlag } from '../types/license';
import { 
  DEFAULT_FREE_LICENSE, 
  DEFAULT_TRIAL_LICENSE,
  FEATURES 
} from '../types/license';

interface LicenseState {
  license: License;
  isValidating: boolean;
  lastError: string | null;
}

const CACHE_KEY = 'vibeforge:license';
const CACHE_TTL = 24 * 60 * 60 * 1000;

class LicenseStore {
  private _state = $state<LicenseState>({
    license: DEFAULT_FREE_LICENSE,
    isValidating: false,
    lastError: null,
  });

  get license() { return this._state.license; }
  get tier() { return this._state.license.tier; }
  get isValidating() { return this._state.isValidating; }
  get lastError() { return this._state.lastError; }

  canUseOrchestrator = $derived(
    this._state.license.features.has(FEATURES.ORCHESTRATOR_MULTI_AI) &&
    (this._state.license.limits.orchestratorRunsPerMonth === Infinity ||
     this._state.license.limits.orchestratorUsedThisMonth < this._state.license.limits.orchestratorRunsPerMonth)
  );

  canUseCloudExecution = $derived(
    this._state.license.features.has(FEATURES.EXECUTION_CLOUD)
  );

  canUseModelComparison = $derived(
    this._state.license.features.has(FEATURES.COMPARISON_SIDE_BY_SIDE)
  );

  isFree = $derived(this._state.license.tier === 'free');
  isTrial = $derived(this._state.license.tier === 'trial');
  isPro = $derived(this._state.license.tier === 'pro' || this._state.license.tier === 'enterprise');

  isTrialExpired = $derived(
    this._state.license.tier === 'trial' &&
    this._state.license.trialEndsAt !== null &&
    new Date() > this._state.license.trialEndsAt
  );

  trialDaysRemaining = $derived(() => {
    if (this._state.license.tier !== 'trial' || !this._state.license.trialEndsAt) {
      return null;
    }
    const diff = this._state.license.trialEndsAt.getTime() - Date.now();
    return Math.max(0, Math.ceil(diff / (24 * 60 * 60 * 1000)));
  });

  hasFeature(feature: FeatureFlag): boolean {
    return this._state.license.features.has(feature);
  }

  async checkLicense(): Promise<void> {
    const cached = this.loadFromCache();
    if (cached && !this.isCacheExpired(cached)) {
      this._state.license = cached;
      return;
    }

    this._state.isValidating = true;
    this._state.lastError = null;

    try {
      const response = await fetch('https://api.vibeforge.dev/license/validate', {
        headers: {
          'Authorization': `Bearer ${this.getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) throw new Error(`License validation failed: ${response.status}`);

      const data = await response.json();
      const license: License = {
        ...data.license,
        expiresAt: data.license.expiresAt ? new Date(data.license.expiresAt) : null,
        trialEndsAt: data.license.trialEndsAt ? new Date(data.license.trialEndsAt) : null,
        features: new Set(data.license.features),
        checkedAt: Date.now(),
      };

      this._state.license = license;
      this.saveToCache(license);
    } catch (error) {
      if (cached) this._state.license = cached;
      else this._state.license = DEFAULT_FREE_LICENSE;
      this._state.lastError = error instanceof Error ? error.message : 'Unknown error';
    } finally {
      this._state.isValidating = false;
    }
  }

  async startTrial(email: string): Promise<boolean> {
    this._state.isValidating = true;
    this._state.lastError = null;

    try {
      const response = await fetch('https://api.vibeforge.dev/license/trial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) throw new Error('Failed to start trial');

      const data = await response.json();
      const license: License = {
        ...DEFAULT_TRIAL_LICENSE,
        userId: data.userId,
        email,
        trialEndsAt: new Date(data.trialEndsAt),
        checkedAt: Date.now(),
      };

      this._state.license = license;
      this.saveToCache(license);
      return true;
    } catch (error) {
      this._state.lastError = error instanceof Error ? error.message : 'Unknown error';
      return false;
    } finally {
      this._state.isValidating = false;
    }
  }

  incrementOrchestratorUsage(): void {
    if (this._state.license.limits.orchestratorRunsPerMonth !== Infinity) {
      this._state.license.limits.orchestratorUsedThisMonth += 1;
      this.saveToCache(this._state.license);
    }
  }

  private loadFromCache(): License | null {
    if (!browser) return null;
    try {
      const stored = localStorage.getItem(CACHE_KEY);
      if (!stored) return null;
      const data = JSON.parse(stored);
      return {
        ...data,
        expiresAt: data.expiresAt ? new Date(data.expiresAt) : null,
        trialEndsAt: data.trialEndsAt ? new Date(data.trialEndsAt) : null,
        features: new Set(data.features),
      };
    } catch { return null; }
  }

  private saveToCache(license: License): void {
    if (!browser) return;
    const data = { ...license, features: Array.from(license.features) };
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  }

  private isCacheExpired(license: License): boolean {
    return Date.now() - license.checkedAt > CACHE_TTL;
  }

  private getAuthToken(): string {
    if (!browser) return '';
    return localStorage.getItem('vibeforge:auth_token') ?? '';
  }

  constructor() {
    if (browser) {
      const cached = this.loadFromCache();
      if (cached) this._state.license = cached;
    }
  }
}

export const licenseStore = new LicenseStore();
```

---

## Task 3: Create FeatureGate.svelte

Create `src/lib/components/FeatureGate.svelte`:

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { FeatureFlag } from '$lib/core/types/license';
  import { licenseStore } from '$lib/core/stores/license.svelte';
  import UpgradePrompt from './UpgradePrompt.svelte';

  interface Props {
    feature: FeatureFlag;
    children: Snippet;
    fallback?: Snippet;
    showUpgrade?: boolean;
  }

  let { feature, children, fallback, showUpgrade = true }: Props = $props();
  const hasFeature = $derived(licenseStore.hasFeature(feature));
</script>

{#if hasFeature}
  {@render children()}
{:else if fallback}
  {@render fallback()}
{:else if showUpgrade}
  <UpgradePrompt {feature} />
{/if}
```

---

## Task 4: Create UpgradePrompt.svelte

Create `src/lib/components/UpgradePrompt.svelte`:

```svelte
<script lang="ts">
  import type { FeatureFlag } from '$lib/core/types/license';
  import { licenseStore } from '$lib/core/stores/license.svelte';
  import { Button } from '$lib/components/ui';

  interface Props { feature: FeatureFlag; compact?: boolean; }
  let { feature, compact = false }: Props = $props();

  let showTrialModal = $state(false);
  let email = $state('');
  let isSubmitting = $state(false);

  const featureNames: Record<string, string> = {
    'orchestrator.multiAI': 'Multi-AI Orchestrator',
    'execution.cloud': 'Cloud Execution',
    'comparison.sideBySide': 'Model Comparison',
  };

  async function startTrial() {
    if (!email) return;
    isSubmitting = true;
    const success = await licenseStore.startTrial(email);
    if (success) showTrialModal = false;
    isSubmitting = false;
  }
</script>

{#if compact}
  <button class="upgrade-badge" onclick={() => showTrialModal = true}>PRO</button>
{:else}
  <div class="upgrade-prompt">
    <div class="prompt-icon">✨</div>
    <h3>{featureNames[feature] ?? 'This feature'}</h3>
    <p>This is a Pro feature. Start a free trial to unlock it.</p>
    <Button variant="primary" onclick={() => showTrialModal = true}>
      Start 14-Day Free Trial
    </Button>
  </div>
{/if}

{#if showTrialModal}
  <div class="modal-backdrop" onclick={() => showTrialModal = false}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <h2>Start Your Free Trial</h2>
      <input type="email" bind:value={email} placeholder="you@example.com" />
      <div class="modal-actions">
        <Button variant="ghost" onclick={() => showTrialModal = false}>Cancel</Button>
        <Button variant="primary" onclick={startTrial} disabled={!email || isSubmitting}>
          {isSubmitting ? 'Starting...' : 'Start Trial'}
        </Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .upgrade-badge { position: absolute; top: -0.5rem; right: -0.5rem; padding: 0.125rem 0.5rem; background: var(--amber-500); color: var(--blacksteel-950); font-size: 0.625rem; font-weight: 700; border-radius: 1rem; border: none; cursor: pointer; }
  .upgrade-prompt { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; padding: 2rem; text-align: center; background: var(--surface-secondary); border: 1px solid var(--border-primary); border-radius: 0.5rem; }
  .prompt-icon { font-size: 2rem; }
  .upgrade-prompt h3 { font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin: 0; }
  .upgrade-prompt p { color: var(--text-secondary); margin: 0; }
  .modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .modal { background: var(--surface-primary); border: 1px solid var(--border-primary); border-radius: 0.75rem; padding: 1.5rem; max-width: 24rem; width: 100%; }
  .modal h2 { font-size: 1.25rem; margin: 0 0 1rem; color: var(--text-primary); }
  .modal input { width: 100%; padding: 0.625rem; background: var(--surface-secondary); border: 1px solid var(--border-primary); border-radius: 0.375rem; color: var(--text-primary); margin-bottom: 1rem; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
</style>
```

---

## Task 5: Create TrialBanner.svelte

Create `src/lib/components/TrialBanner.svelte`:

```svelte
<script lang="ts">
  import { licenseStore } from '$lib/core/stores/license.svelte';
  const daysRemaining = licenseStore.trialDaysRemaining;
</script>

{#if licenseStore.isTrial && daysRemaining() !== null}
  <div class="trial-banner" class:expiring={daysRemaining()! <= 3}>
    <span>⏳ {daysRemaining()} days left in your trial</span>
    <a href="https://vibeforge.dev/pricing" target="_blank">Upgrade to Pro</a>
  </div>
{:else if licenseStore.isTrialExpired}
  <div class="trial-banner expired">
    <span>⚠️ Your trial has expired</span>
    <a href="https://vibeforge.dev/pricing" target="_blank">Upgrade to Pro</a>
  </div>
{/if}

<style>
  .trial-banner { display: flex; align-items: center; justify-content: center; gap: 0.75rem; padding: 0.5rem 1rem; background: var(--blue-900); color: var(--blue-200); font-size: 0.875rem; }
  .trial-banner.expiring { background: var(--amber-900); color: var(--amber-200); }
  .trial-banner.expired { background: var(--red-900); color: var(--red-200); }
  .trial-banner a { color: inherit; font-weight: 600; text-decoration: underline; }
</style>
```

---

## Task 6: Create License Store Tests

Create `src/tests/stores/license.test.ts` with comprehensive tests for:
- Initial state (free tier)
- Feature checks
- License validation
- Trial start
- Usage tracking
- Cache behavior

---

## Task 7: Verify and Checkpoint

```bash
pnpm check
pnpm test src/tests/stores/license.test.ts
git add -A
git commit -m "feat(license): Add license store and feature gates for freemium model"
git tag step-1-license-complete
```

---

# Step 2: Planning Types & Data Models (~1 hour)

## 2.1 Claude Code Prompt

```
You are implementing the Planning Types for VibeForge's Multi-AI Orchestrator (Cortex).

Create `src/lib/workbench/planning/types/index.ts` with:

```typescript
export type StageType = 'initial' | 'review' | 'refinement' | 'final';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type Provider = 'anthropic' | 'openai' | 'xai' | 'google';
export type RequestType = 'feature' | 'refactor' | 'bugfix' | 'analysis';

export interface PlanningStage {
  id: string;
  index: number;
  type: StageType;
  model: string;
  provider: Provider;
  status: StageStatus;
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  prompt: string;
  inputContext: string;
  output?: string;
  summary?: string;
  tokensUsed?: number;
  cost?: number;
  userInjection?: string;
}

export interface PlanningRequest {
  type: RequestType;
  title: string;
  description: string;
  context?: string;
  codeContext?: string[];
}

export interface PlanningConfig {
  initialModel: 'chatgpt' | 'grok' | 'gemini';
  reviewModel: 'claude';
  refinementModel: 'chatgpt' | 'grok' | 'gemini';
  finalModel: 'claude';
  maxIterations: number;
  autoAdvance: boolean;
  pauseAfterReview: boolean;
  requireTestCoverage: boolean;
  targetCoverage: 40 | 60 | 80 | 100;
}

export const DEFAULT_PLANNING_CONFIG: PlanningConfig = {
  initialModel: 'chatgpt',
  reviewModel: 'claude',
  refinementModel: 'chatgpt',
  finalModel: 'claude',
  maxIterations: 2,
  autoAdvance: true,
  pauseAfterReview: false,
  requireTestCoverage: true,
  targetCoverage: 100,
};

export interface PlanningSession {
  id: string;
  createdAt: string;
  updatedAt: string;
  status: 'active' | 'paused' | 'completed' | 'failed';
  request: PlanningRequest;
  config: PlanningConfig;
  stages: PlanningStage[];
  currentStageIndex: number;
  finalPlan?: TwoFileDeliverable;
  error?: string;
}

export interface TwoFileDeliverable {
  implementationPlan: { content: string; filename: string; sections: string[]; };
  claudeCodePrompt: { content: string; filename: string; phases: number; estimatedTime: string; };
}

export interface ModelCallOptions {
  model: string;
  provider: Provider;
  prompt: string;
  systemPrompt?: string;
  maxTokens?: number;
  temperature?: number;
  onProgress?: (chunk: string) => void;
}

export interface ModelCallResult {
  content: string;
  tokensUsed: number;
  cost: number;
  model: string;
  provider: Provider;
  duration: number;
}

export function createEmptySession(request: PlanningRequest, config = DEFAULT_PLANNING_CONFIG): PlanningSession {
  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    status: 'active',
    request,
    config,
    stages: [],
    currentStageIndex: 0,
  };
}

export function getStageLabel(stage: PlanningStage): string {
  const labels = { initial: 'Initial Planning', review: 'Review & Critique', refinement: 'Refinement', final: 'Final Plan' };
  return labels[stage.type];
}

export function getProviderLabel(provider: Provider): string {
  const labels = { anthropic: 'Claude', openai: 'ChatGPT', xai: 'Grok', google: 'Gemini' };
  return labels[provider];
}
```

Create tests in `src/tests/planning/types.test.ts`.

```bash
git add -A && git commit -m "feat(planning): Add planning types" && git tag step-2-types-complete
```
```

---

# Step 3: Model Router Service (~2 hours)

## 3.1 Claude Code Prompt

```
Create `src/lib/workbench/planning/services/modelRouter.ts`:

A ModelRouter class that:
- Calls Anthropic, OpenAI, xAI, and Google APIs
- Handles streaming responses
- Calculates costs
- Supports abort functionality

Key methods:
- `call(options: ModelCallOptions): Promise<ModelCallResult>`
- `abort(): void`

Provider configs:
- Anthropic: api.anthropic.com/v1/messages
- OpenAI: api.openai.com/v1/chat/completions
- xAI: api.x.ai/v1/chat/completions (OpenAI-compatible)
- Google: generativelanguage.googleapis.com/v1beta/models

API keys from localStorage: `vibeforge:apikey:{provider}`

Create comprehensive tests in `src/tests/planning/modelRouter.test.ts`.

```bash
git add -A && git commit -m "feat(planning): Add Model Router" && git tag step-3-router-complete
```
```

---

# Step 4: Planning Orchestrator (~3 hours)

## 4.1 Claude Code Prompt

```
Create the Planning Orchestrator in `src/lib/workbench/planning/services/`:

1. **prompts.ts** - Stage prompt templates:
   - STAGE_1_INITIAL_PLAN (ChatGPT)
   - STAGE_2_REVIEW (Claude)
   - STAGE_3_REFINEMENT (ChatGPT)
   - STAGE_4_FINAL (Claude)

2. **parser.ts** - DeliverableParser class:
   - Parses final output into TwoFileDeliverable
   - Extracts sections, phases, estimated time

3. **orchestrator.ts** - PlanningOrchestrator class:
   - `startSession(request, config, callbacks): Promise<PlanningSession>`
   - `pause()`, `resume()`, `abort()`
   - `injectContext(session, stageIndex, context)`
   - Initializes stages based on config
   - Runs stages sequentially
   - Builds context from previous stages
   - Calls modelRouter for each stage

Callbacks interface:
- onStageStart, onStageProgress, onStageComplete, onStageFailed
- onSessionComplete, onSessionFailed

Create tests in `src/tests/planning/orchestrator.test.ts`.

```bash
git add -A && git commit -m "feat(planning): Add Planning Orchestrator" && git tag step-4-orchestrator-complete
```
```

---

# Summary: Steps 1-4 Complete

After completing Steps 1-4:

| Component | Files |
|-----------|-------|
| **License System** | license.ts types, license.svelte.ts store, FeatureGate, UpgradePrompt, TrialBanner |
| **Planning Types** | Complete type definitions |
| **Model Router** | Multi-provider AI routing |
| **Orchestrator** | 4-stage workflow engine |

**Continue to Steps 5-6 for Planning Store and UI Components.**
