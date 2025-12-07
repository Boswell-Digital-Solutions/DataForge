# VibeForge: Multi-AI Planning & Execution Engine

## Overview

This feature transforms VibeForge into an **orchestration layer** for Charles's AI Engineering Workflow. Instead of single-model execution, VibeForge manages the collaborative multi-AI planning process:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CHARLES'S AI ENGINEERING WORKFLOW                         │
│                        (Automated by VibeForge)                              │
└─────────────────────────────────────────────────────────────────────────────┘

    User Request (Feature, Refactor, Bug Fix)
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │  STAGE 1: INITIAL PLANNING          │
    │  Model: ChatGPT                     │
    │  Output: Draft plan, structure,     │
    │          initial approach           │
    └─────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │  STAGE 2: REVIEW & IMPROVE          │
    │  Model: Claude                      │
    │  Input: ChatGPT's draft             │
    │  Output: Critiques, gaps,           │
    │          improvements, questions    │
    └─────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │  STAGE 3: REFINEMENT                │
    │  Model: ChatGPT                     │
    │  Input: Claude's feedback           │
    │  Output: Addressed concerns,        │
    │          expanded details           │
    └─────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │  STAGE 4: FINAL PLAN                │
    │  Model: Claude                      │
    │  Input: Full conversation history   │
    │  Output: Two-File Deliverable       │
    │    • Implementation Plan            │
    │    • Claude Code Prompt             │
    └─────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │  STAGE 5: EXECUTION                 │
    │  Tool: Claude Code                  │
    │  Input: Claude Code Prompt          │
    │  Output: Implemented code           │
    └─────────────────────────────────────┘
```

---

## The Collaborative Planning Flow

### What The User Sees

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VIBEFORGE PLANNING VIEW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Request] ─────────────────────────────────────────────────────────────    │
│  │ Add GitHub OAuth integration with repository selection                    │
│  │ and branch picker for the source panel.                                  │
│  └──────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PLANNING STAGES                                          [Options ▼]    │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  ✅ Stage 1: Initial Plan (ChatGPT)              2m 34s              │   │
│  │     └─ Generated structure with 5 phases                             │   │
│  │                                                                      │   │
│  │  ✅ Stage 2: Review (Claude)                     1m 12s              │   │
│  │     └─ Identified 3 gaps, suggested improvements                     │   │
│  │                                                                      │   │
│  │  ✅ Stage 3: Refinement (ChatGPT)                1m 45s              │   │
│  │     └─ Addressed security concern, added error handling              │   │
│  │                                                                      │   │
│  │  ⏳ Stage 4: Final Plan (Claude)                 running...          │   │
│  │     └─ Generating two-file deliverable...                            │   │
│  │                                                                      │   │
│  │  ⬚ Stage 5: Execution                           pending              │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CONVERSATION HISTORY                              [Collapse ▼]      │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  🤖 ChatGPT (Stage 1):                                              │   │
│  │  "Here's my initial plan for GitHub OAuth integration..."            │   │
│  │  [View Full Response]                                               │   │
│  │                                                                      │   │
│  │  🧠 Claude (Stage 2):                                               │   │
│  │  "Good start. I see three areas that need attention:                │   │
│  │   1. Token refresh handling is missing..."                          │   │
│  │  [View Full Response]                                               │   │
│  │                                                                      │   │
│  │  🤖 ChatGPT (Stage 3):                                              │   │
│  │  "You're right. Here's the updated plan with token refresh..."      │   │
│  │  [View Full Response]                                               │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  [◀ Back]  [⏸ Pause]  [▶ Continue]  [🔄 Restart Stage]  [✓ Approve Plan]    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### User Control Points

The user can intervene at any stage:

| Control | Description |
|---------|-------------|
| **Pause** | Stop the workflow to review current state |
| **Inject Context** | Add additional information before next stage |
| **Restart Stage** | Re-run current stage with modifications |
| **Skip Stage** | Move to next stage (if confident) |
| **Add Iteration** | Insert another ChatGPT↔Claude round |
| **Approve Plan** | Accept final plan and proceed to execution |
| **Edit Plan** | Manually modify the final deliverable |

---

## Data Models

### Planning Session

```typescript
interface PlanningSession {
  id: string;
  createdAt: string;
  updatedAt: string;
  status: 'active' | 'paused' | 'completed' | 'failed';
  
  // Source
  request: {
    type: 'feature' | 'refactor' | 'bugfix' | 'analysis';
    title: string;
    description: string;
    context?: string;           // Additional context (e.g., analysis results)
    codeContext?: string[];     // Relevant file paths
  };
  
  // Configuration
  config: PlanningConfig;
  
  // Stages
  stages: PlanningStage[];
  currentStageIndex: number;
  
  // Results
  finalPlan?: TwoFileDeliverable;
  executionResult?: ExecutionResult;
}

interface PlanningConfig {
  // Model routing
  initialModel: 'chatgpt' | 'grok' | 'gemini';    // Default: chatgpt
  reviewModel: 'claude';                           // Always Claude
  refinementModel: 'chatgpt' | 'grok' | 'gemini'; // Default: chatgpt
  finalModel: 'claude';                            // Always Claude
  
  // Workflow options
  maxIterations: number;        // Default: 2 (ChatGPT→Claude→ChatGPT→Claude)
  autoAdvance: boolean;         // Auto-continue to next stage? Default: true
  pauseAfterReview: boolean;    // Pause after Claude review? Default: false
  
  // Quality settings
  requireTestCoverage: boolean; // Include test specs? Default: true
  targetCoverage: number;       // 40 | 60 | 80 | 100. Default: 100
  includeBusinessContext: boolean;
}

interface PlanningStage {
  id: string;
  index: number;
  type: 'initial' | 'review' | 'refinement' | 'final' | 'execution';
  model: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  
  // Timing
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  
  // Input
  prompt: string;
  inputContext: string;         // Previous stage output + accumulated context
  
  // Output
  output?: string;
  summary?: string;             // Brief description of what was produced
  
  // Metadata
  tokensUsed?: number;
  cost?: number;
  
  // User intervention
  userInjection?: string;       // Context added by user before this stage
  wasRestarted?: boolean;
}

interface TwoFileDeliverable {
  implementationPlan: {
    content: string;
    filename: string;           // e.g., "GITHUB_OAUTH_IMPLEMENTATION.md"
    sections: string[];         // For navigation
  };
  claudeCodePrompt: {
    content: string;
    filename: string;           // e.g., "GITHUB_OAUTH_PROMPT.md"
    phases: number;             // Number of implementation phases
    estimatedTime: string;      // e.g., "~4 hours"
  };
}
```

---

## Stage Prompts

### Stage 1: Initial Planning (ChatGPT)

```typescript
const STAGE_1_PROMPT = `
You are helping plan a software feature for VibeForge, an AI engineering workbench.

**User Request:**
{request.title}

{request.description}

**Project Context:**
- Framework: SvelteKit with Svelte 5 (runes: $state, $derived, $effect)
- Styling: Tailwind CSS
- Desktop: Tauri
- Core requirement: 100% test coverage

{request.context}

**Your Task:**
Create an initial implementation plan with:

1. **Overview** - What this feature does and why
2. **Architecture** - How it fits into the existing system
3. **Components** - New files/components needed
4. **Data Models** - Types, interfaces, database changes
5. **API Endpoints** - If any backend changes needed
6. **Implementation Phases** - Break into logical phases
7. **Potential Challenges** - What might be tricky

Be thorough but don't over-engineer. Focus on practical implementation.
`;
```

### Stage 2: Review (Claude)

```typescript
const STAGE_2_PROMPT = `
You are reviewing a software implementation plan. Your role is to:
- Identify gaps and missing pieces
- Suggest improvements
- Question assumptions
- Ensure production-readiness

**Original User Request:**
{request.title}
{request.description}

**Initial Plan (from ChatGPT):**
{stage1Output}

**Review Criteria:**
1. Does this cover all edge cases?
2. Is error handling adequate?
3. Are there security concerns?
4. Will this integrate well with existing code?
5. Is the phasing logical?
6. What's missing?

**Your Output:**
Provide a structured review with:
- ✅ What's good about this plan
- ⚠️ Concerns or gaps
- 💡 Suggested improvements
- ❓ Questions that need answers

Be constructively critical. Improvements enthusiastically encouraged.
`;
```

### Stage 3: Refinement (ChatGPT)

```typescript
const STAGE_3_PROMPT = `
You previously created an implementation plan. Claude has reviewed it and provided feedback.

**Original Plan:**
{stage1Output}

**Claude's Review:**
{stage2Output}

**Your Task:**
Address Claude's feedback and refine the plan:
1. Fix identified gaps
2. Incorporate suggested improvements
3. Answer questions (or note what needs user input)
4. Add any missing details

Output an updated, comprehensive plan that addresses all concerns.
`;
```

### Stage 4: Final Plan (Claude)

```typescript
const STAGE_4_PROMPT = `
You are creating the final implementation deliverables for a VibeForge feature.

**Full Planning History:**
---
Request: {request.title}
{request.description}
---
Initial Plan (ChatGPT): {stage1Output}
---
Review (Claude): {stage2Output}
---
Refined Plan (ChatGPT): {stage3Output}
---

**Your Task:**
Create the Two-File Deliverable:

## FILE 1: Implementation Plan
A detailed document including:
- Complete architecture
- All file paths with full code
- Database schemas (if any)
- API endpoints (if any)
- Test specifications
- Success criteria

## FILE 2: Claude Code Prompt
A prompt that can be pasted into Claude Code for autonomous execution:
- Phase-by-phase instructions
- Architecture rules and patterns
- Quality gates (pnpm check, test coverage)
- Git checkpoint instructions

**Format:**
Output as two clearly marked sections:
---BEGIN IMPLEMENTATION PLAN---
[content]
---END IMPLEMENTATION PLAN---

---BEGIN CLAUDE CODE PROMPT---
[content]
---END CLAUDE CODE PROMPT---

Remember: 100% test coverage is mandatory.
`;
```

---

## Architecture

### Directory Structure

```
src/lib/workbench/
├── planning/                          🆕 NEW
│   ├── PlanningPanel.svelte           # Main planning view
│   ├── PlanningStages.svelte          # Stage list/progress
│   ├── StageCard.svelte               # Individual stage display
│   ├── ConversationHistory.svelte     # Full conversation view
│   ├── PlanningControls.svelte        # User control buttons
│   ├── RequestInput.svelte            # Initial request input
│   ├── ContextInjector.svelte         # Add context mid-flow
│   ├── FinalPlanViewer.svelte         # View/edit final deliverable
│   ├── index.ts
│   │
│   └── execution/
│       ├── ExecutionPanel.svelte      # Execute final plan
│       ├── ClaudeCodeExport.svelte    # Copy/download prompt
│       └── index.ts
│
├── stores/
│   └── planning.svelte.ts             🆕 NEW
│
└── services/
    ├── PlanningOrchestrator.ts        🆕 NEW - Routes between models
    ├── ModelRouter.ts                 🆕 NEW - API calls to different models
    └── PlanParser.ts                  🆕 NEW - Parses final deliverable
```

### PlanningOrchestrator

The core service that manages the multi-AI workflow:

```typescript
// src/lib/workbench/services/PlanningOrchestrator.ts

import { ModelRouter } from './ModelRouter';
import { PlanParser } from './PlanParser';
import type { PlanningSession, PlanningStage, TwoFileDeliverable } from '../types/planning';

export class PlanningOrchestrator {
  private router: ModelRouter;
  private parser: PlanParser;
  private abortController: AbortController | null = null;
  
  constructor() {
    this.router = new ModelRouter();
    this.parser = new PlanParser();
  }
  
  /**
   * Start a new planning session
   */
  async startSession(
    request: PlanningSession['request'],
    config: PlanningSession['config'],
    callbacks: {
      onStageStart: (stage: PlanningStage) => void;
      onStageProgress: (stage: PlanningStage, progress: number) => void;
      onStageComplete: (stage: PlanningStage) => void;
      onStageFailed: (stage: PlanningStage, error: string) => void;
      onSessionComplete: (deliverable: TwoFileDeliverable) => void;
      onSessionFailed: (error: string) => void;
    }
  ): Promise<PlanningSession> {
    this.abortController = new AbortController();
    
    const session: PlanningSession = {
      id: `session-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'active',
      request,
      config,
      stages: this.initializeStages(config),
      currentStageIndex: 0
    };
    
    try {
      await this.runStages(session, callbacks);
      return session;
    } catch (error) {
      session.status = 'failed';
      callbacks.onSessionFailed(error instanceof Error ? error.message : 'Unknown error');
      return session;
    }
  }
  
  /**
   * Initialize stages based on config
   */
  private initializeStages(config: PlanningSession['config']): PlanningStage[] {
    const stages: PlanningStage[] = [
      {
        id: 'stage-1',
        index: 0,
        type: 'initial',
        model: config.initialModel,
        status: 'pending',
        prompt: '',
        inputContext: ''
      },
      {
        id: 'stage-2',
        index: 1,
        type: 'review',
        model: config.reviewModel,
        status: 'pending',
        prompt: '',
        inputContext: ''
      }
    ];
    
    // Add iterations based on config
    for (let i = 1; i < config.maxIterations; i++) {
      stages.push({
        id: `stage-${stages.length + 1}`,
        index: stages.length,
        type: 'refinement',
        model: config.refinementModel,
        status: 'pending',
        prompt: '',
        inputContext: ''
      });
      
      if (i < config.maxIterations - 1) {
        stages.push({
          id: `stage-${stages.length + 1}`,
          index: stages.length,
          type: 'review',
          model: config.reviewModel,
          status: 'pending',
          prompt: '',
          inputContext: ''
        });
      }
    }
    
    // Always end with Claude's final plan
    stages.push({
      id: `stage-final`,
      index: stages.length,
      type: 'final',
      model: 'claude',
      status: 'pending',
      prompt: '',
      inputContext: ''
    });
    
    return stages;
  }
  
  /**
   * Run through all stages
   */
  private async runStages(
    session: PlanningSession,
    callbacks: Parameters<typeof this.startSession>[2]
  ): Promise<void> {
    for (let i = session.currentStageIndex; i < session.stages.length; i++) {
      if (this.abortController?.signal.aborted) {
        session.status = 'paused';
        return;
      }
      
      const stage = session.stages[i];
      session.currentStageIndex = i;
      
      // Build context from previous stages
      stage.inputContext = this.buildContext(session, i);
      stage.prompt = this.buildPrompt(stage, session);
      
      callbacks.onStageStart(stage);
      stage.status = 'running';
      stage.startedAt = new Date().toISOString();
      
      try {
        const result = await this.router.call(
          stage.model,
          stage.prompt,
          (progress) => callbacks.onStageProgress(stage, progress)
        );
        
        stage.output = result.content;
        stage.summary = this.summarizeOutput(stage.type, result.content);
        stage.tokensUsed = result.tokensUsed;
        stage.cost = result.cost;
        stage.status = 'completed';
        stage.completedAt = new Date().toISOString();
        stage.duration = Date.now() - new Date(stage.startedAt).getTime();
        
        callbacks.onStageComplete(stage);
        
        // Parse final deliverable
        if (stage.type === 'final') {
          session.finalPlan = this.parser.parseDeliverable(result.content);
          session.status = 'completed';
          callbacks.onSessionComplete(session.finalPlan);
        }
        
      } catch (error) {
        stage.status = 'failed';
        callbacks.onStageFailed(stage, error instanceof Error ? error.message : 'Failed');
        throw error;
      }
    }
  }
  
  /**
   * Build accumulated context for a stage
   */
  private buildContext(session: PlanningSession, stageIndex: number): string {
    let context = `**Original Request:**\n${session.request.title}\n\n${session.request.description}\n`;
    
    if (session.request.context) {
      context += `\n**Additional Context:**\n${session.request.context}\n`;
    }
    
    // Add previous stage outputs
    for (let i = 0; i < stageIndex; i++) {
      const prev = session.stages[i];
      if (prev.output) {
        const label = this.getStageLabel(prev);
        context += `\n---\n**${label}:**\n${prev.output}\n`;
      }
    }
    
    return context;
  }
  
  /**
   * Build prompt for a stage
   */
  private buildPrompt(stage: PlanningStage, session: PlanningSession): string {
    const templates = {
      initial: STAGE_1_PROMPT,
      review: STAGE_2_PROMPT,
      refinement: STAGE_3_PROMPT,
      final: STAGE_4_PROMPT
    };
    
    let prompt = templates[stage.type];
    
    // Replace placeholders
    prompt = prompt.replace('{request.title}', session.request.title);
    prompt = prompt.replace('{request.description}', session.request.description);
    prompt = prompt.replace('{request.context}', session.request.context || '');
    
    // Add previous outputs
    session.stages.forEach((s, i) => {
      if (s.output) {
        prompt = prompt.replace(`{stage${i + 1}Output}`, s.output);
      }
    });
    
    // Add user injection if present
    if (stage.userInjection) {
      prompt += `\n\n**User Added Context:**\n${stage.userInjection}`;
    }
    
    return prompt;
  }
  
  private getStageLabel(stage: PlanningStage): string {
    const labels = {
      initial: `Initial Plan (${stage.model})`,
      review: `Review (${stage.model})`,
      refinement: `Refinement (${stage.model})`,
      final: `Final Plan (${stage.model})`
    };
    return labels[stage.type];
  }
  
  private summarizeOutput(type: PlanningStage['type'], output: string): string {
    // Extract first meaningful line or generate summary
    const lines = output.split('\n').filter(l => l.trim());
    if (type === 'review') {
      const concerns = (output.match(/⚠️/g) || []).length;
      const improvements = (output.match(/💡/g) || []).length;
      return `${concerns} concerns, ${improvements} improvements suggested`;
    }
    return lines[0]?.substring(0, 100) || 'Generated output';
  }
  
  /**
   * Pause the current session
   */
  pause(): void {
    this.abortController?.abort();
  }
  
  /**
   * Resume a paused session
   */
  async resume(
    session: PlanningSession,
    callbacks: Parameters<typeof this.startSession>[2]
  ): Promise<PlanningSession> {
    session.status = 'active';
    this.abortController = new AbortController();
    await this.runStages(session, callbacks);
    return session;
  }
  
  /**
   * Inject user context before a stage
   */
  injectContext(session: PlanningSession, stageIndex: number, context: string): void {
    if (session.stages[stageIndex]) {
      session.stages[stageIndex].userInjection = context;
    }
  }
  
  /**
   * Restart a specific stage
   */
  async restartStage(
    session: PlanningSession,
    stageIndex: number,
    callbacks: Parameters<typeof this.startSession>[2]
  ): Promise<void> {
    // Reset this stage and all following
    for (let i = stageIndex; i < session.stages.length; i++) {
      session.stages[i].status = 'pending';
      session.stages[i].output = undefined;
      session.stages[i].wasRestarted = i === stageIndex;
    }
    
    session.currentStageIndex = stageIndex;
    await this.runStages(session, callbacks);
  }
}

// Template constants (abbreviated - full versions above)
const STAGE_1_PROMPT = `...`;
const STAGE_2_PROMPT = `...`;
const STAGE_3_PROMPT = `...`;
const STAGE_4_PROMPT = `...`;

export const planningOrchestrator = new PlanningOrchestrator();
```

### ModelRouter

Routes API calls to different AI providers:

```typescript
// src/lib/workbench/services/ModelRouter.ts

interface ModelCallResult {
  content: string;
  tokensUsed: number;
  cost: number;
}

export class ModelRouter {
  private endpoints = {
    chatgpt: '/api/ai/openai',
    claude: '/api/ai/anthropic',
    grok: '/api/ai/xai',
    gemini: '/api/ai/google'
  };
  
  async call(
    model: string,
    prompt: string,
    onProgress?: (progress: number) => void
  ): Promise<ModelCallResult> {
    onProgress?.(10);
    
    const endpoint = this.getEndpoint(model);
    const body = this.buildRequestBody(model, prompt);
    
    onProgress?.(30);
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    
    onProgress?.(70);
    
    if (!response.ok) {
      throw new Error(`${model} API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    onProgress?.(100);
    
    return {
      content: this.extractContent(model, data),
      tokensUsed: this.extractTokens(model, data),
      cost: this.calculateCost(model, data)
    };
  }
  
  private getEndpoint(model: string): string {
    if (model.includes('gpt')) return this.endpoints.chatgpt;
    if (model === 'claude') return this.endpoints.claude;
    if (model === 'grok') return this.endpoints.grok;
    if (model === 'gemini') return this.endpoints.gemini;
    return this.endpoints.chatgpt; // Default
  }
  
  private buildRequestBody(model: string, prompt: string): object {
    // Model-specific request formatting
    if (model.includes('gpt') || model === 'chatgpt') {
      return {
        model: 'gpt-4-turbo',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 8000
      };
    }
    
    if (model === 'claude') {
      return {
        model: 'claude-sonnet-4-20250514',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 8000
      };
    }
    
    // Default format
    return {
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 8000
    };
  }
  
  private extractContent(model: string, data: any): string {
    // Handle different response formats
    if (data.choices?.[0]?.message?.content) {
      return data.choices[0].message.content; // OpenAI format
    }
    if (data.content?.[0]?.text) {
      return data.content[0].text; // Anthropic format
    }
    if (data.candidates?.[0]?.content?.parts?.[0]?.text) {
      return data.candidates[0].content.parts[0].text; // Google format
    }
    return data.response || data.text || '';
  }
  
  private extractTokens(model: string, data: any): number {
    return data.usage?.total_tokens || 
           data.usage?.input_tokens + data.usage?.output_tokens ||
           0;
  }
  
  private calculateCost(model: string, data: any): number {
    // Rough cost estimates per 1K tokens
    const rates: Record<string, number> = {
      'gpt-4-turbo': 0.01,
      'claude': 0.003,
      'grok': 0.005,
      'gemini': 0.00025
    };
    
    const tokens = this.extractTokens(model, data);
    return (tokens / 1000) * (rates[model] || 0.01);
  }
}
```

---

## Store Implementation

```typescript
// src/lib/workbench/stores/planning.svelte.ts

import type { PlanningSession, PlanningStage, TwoFileDeliverable } from '../types/planning';
import { planningOrchestrator } from '../services/PlanningOrchestrator';

interface PlanningState {
  currentSession: PlanningSession | null;
  sessions: PlanningSession[];           // History of past sessions
  isRunning: boolean;
  error: string | null;
}

function createPlanningStore() {
  let state = $state<PlanningState>({
    currentSession: null,
    sessions: [],
    isRunning: false,
    error: null
  });
  
  return {
    get currentSession() { return state.currentSession; },
    get sessions() { return state.sessions; },
    get isRunning() { return state.isRunning; },
    get error() { return state.error; },
    
    get currentStage() {
      if (!state.currentSession) return null;
      return state.currentSession.stages[state.currentSession.currentStageIndex];
    },
    
    get completedStages() {
      return state.currentSession?.stages.filter(s => s.status === 'completed') || [];
    },
    
    get finalPlan() {
      return state.currentSession?.finalPlan || null;
    },
    
    async startNewSession(
      request: PlanningSession['request'],
      config: Partial<PlanningSession['config']> = {}
    ) {
      state.isRunning = true;
      state.error = null;
      
      const fullConfig: PlanningSession['config'] = {
        initialModel: 'chatgpt',
        reviewModel: 'claude',
        refinementModel: 'chatgpt',
        finalModel: 'claude',
        maxIterations: 2,
        autoAdvance: true,
        pauseAfterReview: false,
        requireTestCoverage: true,
        targetCoverage: 100,
        includeBusinessContext: false,
        ...config
      };
      
      const session = await planningOrchestrator.startSession(request, fullConfig, {
        onStageStart: (stage) => {
          // Update state
        },
        onStageProgress: (stage, progress) => {
          // Update progress
        },
        onStageComplete: (stage) => {
          state.currentSession = { ...state.currentSession! };
        },
        onStageFailed: (stage, error) => {
          state.error = error;
        },
        onSessionComplete: (deliverable) => {
          state.isRunning = false;
          state.sessions.push(state.currentSession!);
        },
        onSessionFailed: (error) => {
          state.isRunning = false;
          state.error = error;
        }
      });
      
      state.currentSession = session;
    },
    
    pause() {
      planningOrchestrator.pause();
      state.isRunning = false;
    },
    
    async resume() {
      if (!state.currentSession) return;
      state.isRunning = true;
      // Resume logic
    },
    
    injectContext(context: string) {
      if (!state.currentSession) return;
      const nextIndex = state.currentSession.currentStageIndex + 1;
      planningOrchestrator.injectContext(state.currentSession, nextIndex, context);
    },
    
    async restartCurrentStage() {
      if (!state.currentSession) return;
      state.isRunning = true;
      // Restart logic
    },
    
    clearSession() {
      state.currentSession = null;
      state.error = null;
    }
  };
}

export const planningStore = createPlanningStore();
```

---

## Integration with Analysis

When user clicks "Generate Plan" after analysis:

```typescript
// In analysis handler
async function handleGeneratePlanFromAnalysis() {
  const analysis = analysisStore.current;
  if (!analysis) return;
  
  // Build request from analysis
  const request = {
    type: 'refactor' as const,
    title: `Refactor: Fix ${analysis.issues.length} code issues`,
    description: buildDescriptionFromAnalysis(analysis),
    context: buildContextFromAnalysis(analysis),
    codeContext: analysis.structure.files.map(f => f.path)
  };
  
  // Start planning session
  await planningStore.startNewSession(request, {
    maxIterations: 2,
    requireTestCoverage: true,
    targetCoverage: 100
  });
}

function buildDescriptionFromAnalysis(analysis: CodebaseAnalysis): string {
  const counts = {
    errors: analysis.issues.filter(i => i.severity === 'error').length,
    warnings: analysis.issues.filter(i => i.severity === 'warning').length,
    suggestions: analysis.issues.filter(i => i.severity === 'suggestion').length
  };
  
  return `
The codebase analysis found:
- ${counts.errors} errors
- ${counts.warnings} warnings  
- ${counts.suggestions} suggestions

Key issues:
${analysis.issues.slice(0, 10).map(i => `- ${i.message} (${i.file}:${i.line})`).join('\n')}

Create a plan to systematically address these issues while maintaining 100% test coverage.
  `.trim();
}
```

---

## Implementation Phases

### Phase 1: Data Models & Types (~1 hour)
- Create planning types
- Create session, stage, deliverable interfaces

### Phase 2: Model Router (~2 hours)
- Implement ModelRouter service
- Add endpoints for ChatGPT, Claude, Grok, Gemini
- Handle different response formats
- Add cost calculation

### Phase 3: Planning Orchestrator (~3 hours)
- Implement stage initialization
- Implement context building
- Implement prompt templates
- Implement stage execution flow
- Add pause/resume/restart

### Phase 4: Planning Store (~1 hour)
- Implement planning.svelte.ts
- Wire to orchestrator callbacks

### Phase 5: Planning UI (~4 hours)
- PlanningPanel.svelte
- PlanningStages.svelte (progress view)
- StageCard.svelte (individual stage)
- ConversationHistory.svelte
- PlanningControls.svelte
- RequestInput.svelte
- ContextInjector.svelte

### Phase 6: Final Plan Viewer (~2 hours)
- FinalPlanViewer.svelte
- Two-file display with tabs
- Copy/download buttons
- Claude Code export

### Phase 7: Integration (~2 hours)
- Wire to analysis drawer
- Add to main layout
- Keyboard shortcuts

### Phase 8: Tests (~2 hours)
- Orchestrator tests
- Store tests
- 100% coverage

---

## Total Estimated Time

| Phase | Time |
|-------|------|
| Types | 1h |
| ModelRouter | 2h |
| Orchestrator | 3h |
| Store | 1h |
| Planning UI | 4h |
| Plan Viewer | 2h |
| Integration | 2h |
| Tests | 2h |
| **Total** | **~17 hours** |

---

## Success Criteria

- [ ] Can enter feature request and start planning
- [ ] Stage 1 sends to ChatGPT, shows response
- [ ] Stage 2 sends to Claude with ChatGPT's output, shows review
- [ ] Stage 3 sends back to ChatGPT with Claude's feedback
- [ ] Stage 4 Claude creates final two-file deliverable
- [ ] Can pause/resume at any stage
- [ ] Can inject context before any stage
- [ ] Can restart any stage
- [ ] Final plan viewable in two tabs (Implementation + Prompt)
- [ ] Can copy/download Claude Code prompt
- [ ] Can start from analysis results
- [ ] Full conversation history visible
- [ ] Cost/token tracking per stage
- [ ] 100% test coverage

---

## API Requirements

NeuroForge needs endpoints for multiple providers:

```
POST /api/ai/openai      → ChatGPT
POST /api/ai/anthropic   → Claude  
POST /api/ai/xai         → Grok
POST /api/ai/google      → Gemini
```

Each endpoint should:
- Accept standardized request format
- Return standardized response format
- Handle streaming (optional for MVP)
- Track usage for billing

---

## Future Enhancements

1. **Grok Integration** - Add as alternative to ChatGPT for contrarian view
2. **Gemini Integration** - Add as another option
3. **Custom Stage Flows** - Let users define their own multi-model workflows
4. **Template Library** - Pre-built workflows for common tasks
5. **Collaboration** - Share planning sessions with team
6. **Learning** - Track which model combinations work best
7. **Auto-Iteration** - AI decides when to stop iterating

---

## The Key Differentiator

**No other tool orchestrates multiple AIs for planning.**

- Cursor: Single model (Claude)
- Copilot: Single model (GPT)
- VibeForge: **Multi-AI collaborative planning** that matches how sophisticated AI engineers actually work

This is your workflow, productized.
