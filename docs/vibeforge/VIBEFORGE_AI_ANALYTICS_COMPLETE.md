# VibeForge AI Execution Analytics

**Version:** 1.0  
**Created:** November 26, 2025  
**Total AI Execution Time:** 2-3 hours

---

## Table of Contents

1. [Implementation Plan](#part-1-implementation-plan)
2. [Claude Code Prompt](#part-2-claude-code-prompt)

---

# Part 1: Implementation Plan

## Problem Statement

VibeForge's current estimation and analytics systems assume human developer execution times. With Claude Code autonomous execution, tasks that would take a human 4 hours complete in 15 minutes. This creates:

1. **Inaccurate estimates** - Plans show 96 hours when actual AI time is 6-10 hours
2. **Meaningless variance tracking** - 1500% variance because baseline is wrong
3. **Unusable learning data** - Can't train on mixed human/AI data
4. **Poor UX** - Users see wildly inaccurate time estimates

---

## Solution: Dual-Track Estimation

Track human and AI execution separately, with AI-specific metrics.

### New Type Definitions

```typescript
// src/lib/refactoring/types/execution.ts

export type ExecutorType = 'human' | 'ai-claude-code' | 'ai-other';

export interface AIExecutionMetrics {
  executorType: ExecutorType;
  
  // AI-specific timing (in minutes, not hours)
  estimatedMinutes: number;
  actualMinutes?: number;
  
  // Token/API metrics
  totalTokens?: number;
  inputTokens?: number;
  outputTokens?: number;
  apiCalls?: number;
  retryCount?: number;
  
  // Cost tracking
  estimatedCost?: number;  // USD
  actualCost?: number;
  
  // Quality metrics
  firstPassSuccess: boolean;  // Completed without human intervention
  iterationCount: number;     // How many edit cycles
  testPassedOnFirst: boolean; // Tests passed first try
}

export interface TaskExecution {
  taskId: string;
  status: ExecutionStatus;
  startedAt?: string;
  completedAt?: string;
  
  // EXISTING: Human-oriented (keep for backward compat)
  duration?: number; // Seconds
  
  // NEW: AI-oriented
  aiMetrics?: AIExecutionMetrics;
  
  // ... rest of existing fields
}
```

### Updated Planning Types

```typescript
// src/lib/refactoring/types/planning.ts

export interface RefactoringTask {
  id: string;
  // ... existing fields ...
  
  // EXISTING: Human estimate (keep for reports)
  estimatedHours: number;
  
  // NEW: AI estimate
  estimatedMinutesAI: number;
  
  // NEW: Confidence levels
  humanEstimateConfidence: number;  // 0-1
  aiEstimateConfidence: number;     // 0-1
}

export interface TimeEstimate {
  // EXISTING
  optimistic: number;
  realistic: number;
  pessimistic: number;
  expected: number;
  confidence: number;
  
  // NEW: AI-specific
  aiOptimisticMinutes: number;
  aiRealisticMinutes: number;
  aiPessimisticMinutes: number;
  aiExpectedMinutes: number;
  aiConfidence: number;
}
```

### Updated Learning Types

```typescript
// src/lib/refactoring/types/learning.ts

export interface EstimationFeedback {
  id: string;
  taskCategory: TaskCategory;
  taskDescription: string;
  
  // EXISTING: Human-oriented
  estimatedHours: number;
  actualHours: number;
  accuracy: number;
  
  // NEW: AI-oriented
  executorType: ExecutorType;
  estimatedMinutesAI?: number;
  actualMinutesAI?: number;
  accuracyAI?: number;
  
  // NEW: AI-specific factors
  aiFactors?: {
    codebaseSize: number;       // Files affected
    complexity: 'low' | 'medium' | 'high';
    hasTests: boolean;          // Existing tests to update
    requiresNewTests: boolean;  // Writing new tests
    crossFileChanges: number;   // Number of files modified
    tokenIntensity: 'low' | 'medium' | 'high';
  };
  
  codebaseContext: { ... };
  factors: string[];
}

export interface TaskRecommendation {
  // EXISTING
  taskCategory: TaskCategory;
  taskPattern: string;
  suggestedEstimateHours: number;
  confidence: number;
  
  // NEW: AI-specific
  suggestedEstimateMinutesAI: number;
  aiConfidence: number;
  
  // NEW: Context for AI estimation
  typicalTokenUsage: number;
  typicalIterations: number;
  firstPassSuccessRate: number;
}
```

---

## AI Speed Multipliers

Based on empirical Claude Code execution data:

| Task Category | Multiplier | Human 4h → AI |
|---------------|------------|---------------|
| Documentation | 15x | 16 min |
| Type Safety | 12x | 20 min |
| Code Quality | 10x | 24 min |
| Testing | 8x | 30 min |
| Architecture | 6x | 40 min |

---

## Implementation Phases

### Phase 1: Type Updates (~20 min)

**Files to modify:**
- `src/lib/refactoring/types/execution.ts`
- `src/lib/refactoring/types/planning.ts`
- `src/lib/refactoring/types/learning.ts`

**Changes:**
1. Add `ExecutorType` enum
2. Add `AIExecutionMetrics` interface
3. Add AI fields to `TaskExecution`
4. Add AI estimates to `RefactoringTask`
5. Add AI fields to `EstimationFeedback`
6. Add AI fields to `TaskRecommendation`

### Phase 2: Estimation Engine Updates (~30 min)

**File:** `src/lib/refactoring/planner/EstimationEngine.ts`

**New methods:**
- `humanHoursToAIMinutes(hours, category)` - Convert using multipliers
- `refineAIEstimates(tasks, recommendations)` - Apply learned estimates
- `calculateTotalAIEstimate(tasks)` - Sum AI times
- `formatAITime(minutes)` - Display formatting

### Phase 3: Task Generator Updates (~15 min)

**File:** `src/lib/refactoring/planner/TaskGenerator.ts`

**Changes:**
- Add AI estimates to generated tasks
- Set default confidence levels

### Phase 4: Task Executor Updates (~30 min)

**File:** `src/lib/refactoring/executor/TaskExecutor.ts`

**Changes:**
- Accept `executorType` parameter
- Initialize AI metrics at start
- Capture actual minutes on completion
- Add methods for recording tokens, retries, API calls

### Phase 5: Outcome Analyzer Updates (~20 min)

**File:** `src/lib/refactoring/executor/OutcomeAnalyzer.ts`

**Changes:**
- Generate AI-specific feedback entries
- Calculate AI accuracy separately
- Infer complexity and token intensity

### Phase 6: Learning Loop Updates (~15 min)

**File:** `src/lib/refactoring/executor/LearningLoop.ts`

**Changes:**
- Add `recordAIExecutionFeedback()` method
- Call NeuroForge AI-specific endpoint

### Phase 7: Prompt Generator Updates (~10 min)

**File:** `src/lib/refactoring/planner/PromptGenerator.ts`

**Changes:**
- Show AI time estimates in prompts
- Add AI execution notes

### Phase 8: Tests (~30 min)

**New test files:**
- `EstimationEngine.test.ts` - AI conversion tests
- Additional coverage for new methods

---

## Database Schema Updates (DataForge)

```sql
-- Add AI execution tracking to refactoring tables

ALTER TABLE refactoring_tasks ADD COLUMN estimated_minutes_ai INTEGER;
ALTER TABLE refactoring_tasks ADD COLUMN ai_estimate_confidence DECIMAL(3,2);

ALTER TABLE task_executions ADD COLUMN executor_type VARCHAR(20) DEFAULT 'human';
ALTER TABLE task_executions ADD COLUMN actual_minutes_ai INTEGER;
ALTER TABLE task_executions ADD COLUMN total_tokens INTEGER;
ALTER TABLE task_executions ADD COLUMN api_calls INTEGER;
ALTER TABLE task_executions ADD COLUMN retry_count INTEGER;
ALTER TABLE task_executions ADD COLUMN first_pass_success BOOLEAN;
ALTER TABLE task_executions ADD COLUMN iteration_count INTEGER;

-- AI-specific analytics table
CREATE TABLE ai_execution_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_category VARCHAR(50) NOT NULL,
  executor_type VARCHAR(20) NOT NULL,
  
  -- Timing
  estimated_minutes INTEGER NOT NULL,
  actual_minutes INTEGER,
  accuracy DECIMAL(5,2),
  
  -- Token metrics
  total_tokens INTEGER,
  input_tokens INTEGER,
  output_tokens INTEGER,
  
  -- Quality
  first_pass_success BOOLEAN,
  iteration_count INTEGER,
  
  -- Cost
  estimated_cost DECIMAL(10,4),
  actual_cost DECIMAL(10,4),
  
  -- Context
  codebase_size INTEGER,
  files_affected INTEGER,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_analytics_category ON ai_execution_analytics(task_category);
CREATE INDEX idx_ai_analytics_executor ON ai_execution_analytics(executor_type);
CREATE INDEX idx_ai_analytics_created ON ai_execution_analytics(created_at);
```

---

## Migration Path

All changes are **additive** - existing human-oriented tracking continues to work.

1. **Phase 1-2:** Update types and estimation engine (backward compatible)
2. **Phase 3-4:** Update executors with optional AI metrics
3. **Phase 5:** Add new learning endpoints (parallel to existing)
4. **Phase 6:** Update prompts to show AI estimates

---

## Success Metrics

After implementation:

| Metric | Current | Target |
|--------|---------|--------|
| AI estimate accuracy | N/A | >80% |
| Human estimate accuracy | ~20% (wrong baseline) | Keep for reference |
| First-pass success rate tracking | None | Tracked |
| Token usage per task type | None | Tracked |
| Cost per task tracking | None | Tracked |

---

# Part 2: Claude Code Prompt

## Quick Start

```bash
cd /path/to/vibeforge
claude --dangerously-skip-permissions
# Paste the master prompt below
```

---

## Master Prompt

```
You are implementing AI execution analytics for VibeForge. The current estimation system assumes human developer timelines, but VibeForge uses Claude Code for autonomous execution where tasks complete 10-15x faster.

## Goal
Add AI-specific time tracking, estimation, and analytics while maintaining backward compatibility with existing human-oriented metrics.

## Key Principle
AI execution is measured in MINUTES, not hours. A 4-hour human task takes ~20-30 minutes for Claude Code.

---

### PHASE 1: Type Definitions (~20 min)

#### Step 1.1: Update execution types
**File:** `src/lib/refactoring/types/execution.ts`

Add after existing types:
```typescript
export type ExecutorType = 'human' | 'ai-claude-code' | 'ai-cursor' | 'ai-other';

export interface AIExecutionMetrics {
  executorType: ExecutorType;
  
  // Timing (minutes for AI, not hours)
  estimatedMinutes: number;
  actualMinutes?: number;
  
  // Token/API metrics
  totalTokens?: number;
  inputTokens?: number;
  outputTokens?: number;
  apiCalls?: number;
  retryCount?: number;
  
  // Cost (USD)
  estimatedCost?: number;
  actualCost?: number;
  
  // Quality indicators
  firstPassSuccess: boolean;
  iterationCount: number;
  testPassedOnFirst: boolean;
}
```

Update `TaskExecution` interface - add:
```typescript
  // AI execution metrics (optional, for AI executors)
  aiMetrics?: AIExecutionMetrics;
```

#### Step 1.2: Update planning types
**File:** `src/lib/refactoring/types/planning.ts`

Update `RefactoringTask` interface - add:
```typescript
  // AI-specific estimate (minutes, not hours)
  estimatedMinutesAI: number;
  aiEstimateConfidence: number;  // 0-1
```

Update `TimeEstimate` interface - add:
```typescript
  // AI estimates (in minutes)
  aiOptimisticMinutes: number;
  aiRealisticMinutes: number;
  aiPessimisticMinutes: number;
  aiExpectedMinutes: number;
  aiConfidence: number;
```

#### Step 1.3: Update learning types
**File:** `src/lib/refactoring/types/learning.ts`

Update `EstimationFeedback` interface - add:
```typescript
  // Executor identification
  executorType: ExecutorType;
  
  // AI-specific metrics
  estimatedMinutesAI?: number;
  actualMinutesAI?: number;
  accuracyAI?: number;
  
  // AI execution factors
  aiFactors?: {
    codebaseSize: number;
    complexity: 'low' | 'medium' | 'high';
    hasTests: boolean;
    requiresNewTests: boolean;
    crossFileChanges: number;
    tokenIntensity: 'low' | 'medium' | 'high';
  };
```

Update `TaskRecommendation` interface - add:
```typescript
  // AI-specific recommendations
  suggestedEstimateMinutesAI: number;
  aiConfidence: number;
  typicalTokenUsage?: number;
  typicalIterations?: number;
  firstPassSuccessRate?: number;
```

#### Step 1.4: Update barrel exports
**File:** `src/lib/refactoring/types/index.ts`

Add to exports:
```typescript
export type { ExecutorType, AIExecutionMetrics } from './execution';
```

**Verify:** `pnpm check`

---

### PHASE 2: Estimation Engine (~30 min)

**File:** `src/lib/refactoring/planner/EstimationEngine.ts`

#### Step 2.1: Add AI conversion method
```typescript
/**
 * Speed multipliers: how many times faster AI is vs human
 * Based on empirical Claude Code execution data
 */
private readonly AI_SPEED_MULTIPLIERS: Record<TaskCategory, number> = {
  'testing': 8,           // AI writes tests very fast
  'type-safety': 12,      // Mechanical changes, AI excels
  'code-quality': 10,     // Refactoring is AI strength
  'architecture': 6,      // Requires more reasoning
  'documentation': 15,    // AI writes docs extremely fast
};

/**
 * Converts human hours estimate to AI minutes
 */
humanHoursToAIMinutes(humanHours: number, category: TaskCategory): number {
  const multiplier = this.AI_SPEED_MULTIPLIERS[category] || 10;
  return Math.round((humanHours * 60) / multiplier);
}

/**
 * Formats AI time for display
 */
formatAITime(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}
```

#### Step 2.2: Add AI estimate refinement
```typescript
/**
 * Refines AI estimates using learning data
 */
refineAIEstimates(
  tasks: RefactoringTask[],
  recommendations: TaskRecommendation[] = []
): RefactoringTask[] {
  return tasks.map((task) => {
    const recommendation = this.findMatchingRecommendation(task, recommendations);
    
    if (recommendation && recommendation.aiConfidence > 0.5) {
      return {
        ...task,
        estimatedMinutesAI: recommendation.suggestedEstimateMinutesAI,
        aiEstimateConfidence: recommendation.aiConfidence
      };
    }
    
    // Fallback: derive from human estimate
    return {
      ...task,
      estimatedMinutesAI: this.humanHoursToAIMinutes(
        task.estimatedHours,
        task.category
      ),
      aiEstimateConfidence: 0.3  // Low confidence for derived estimates
    };
  });
}

/**
 * Calculates total AI execution time for all tasks
 */
calculateTotalAIEstimate(tasks: RefactoringTask[]): number {
  return tasks.reduce((sum, task) => sum + (task.estimatedMinutesAI || 0), 0);
}
```

#### Step 2.3: Update existing methods to include AI estimates
In `refineTaskEstimates`, after setting human estimate:
```typescript
// Also set AI estimate
const aiMinutes = this.humanHoursToAIMinutes(refinedEstimate, task.category);
return {
  ...task,
  estimatedHours: refinedEstimate,
  estimatedMinutesAI: aiMinutes,
  aiEstimateConfidence: recommendation ? recommendation.aiConfidence : 0.3
};
```

**Verify:** `pnpm check && pnpm test`

---

### PHASE 3: Task Generator (~15 min)

**File:** `src/lib/refactoring/planner/TaskGenerator.ts`

#### Step 3.1: Add AI estimates to generated tasks
Import EstimationEngine at top:
```typescript
import { EstimationEngine } from './EstimationEngine';
```

Add to class:
```typescript
private estimationEngine = new EstimationEngine();
```

Update `generateFromIssues` - add AI estimate:
```typescript
return {
  title: issue.title,
  // ... existing fields ...
  estimatedHours: this.estimateHoursFromIssue(issue),
  estimatedMinutesAI: this.estimationEngine.humanHoursToAIMinutes(
    this.estimateHoursFromIssue(issue),
    issue.category
  ),
  aiEstimateConfidence: 0.3,  // Default low confidence
  // ... rest of fields ...
};
```

Same for `generateFromMetrics`.

**Verify:** `pnpm check && pnpm test`

---

### PHASE 4: Task Executor (~30 min)

**File:** `src/lib/refactoring/executor/TaskExecutor.ts`

#### Step 4.1: Update executeTask signature
```typescript
async executeTask(
  project: RefactoringProject,
  phaseNumber: number,
  taskId: string,
  executorType: ExecutorType = 'ai-claude-code'
): Promise<RefactoringProject>
```

#### Step 4.2: Initialize AI metrics
After `taskExecution.startedAt = new Date().toISOString();`:
```typescript
// Initialize AI metrics if AI executor
if (executorType.startsWith('ai-')) {
  taskExecution.aiMetrics = {
    executorType,
    estimatedMinutes: planTask.estimatedMinutesAI || 0,
    apiCalls: 0,
    retryCount: 0,
    iterationCount: 1,
    firstPassSuccess: true,
    testPassedOnFirst: true
  };
}
```

#### Step 4.3: Capture AI metrics on completion
Before `taskExecution.status = 'completed';`:
```typescript
// Calculate AI execution time
if (taskExecution.aiMetrics && taskExecution.startedAt) {
  const startTime = new Date(taskExecution.startedAt).getTime();
  const endTime = Date.now();
  taskExecution.aiMetrics.actualMinutes = Math.round((endTime - startTime) / 60000);
}
```

#### Step 4.4: Add methods for AI metric updates
```typescript
/**
 * Records an API call for AI metrics
 */
recordAPICall(project: RefactoringProject, phaseNumber: number, taskId: string): void {
  const task = this.findTask(project, phaseNumber, taskId);
  if (task?.aiMetrics) {
    task.aiMetrics.apiCalls = (task.aiMetrics.apiCalls || 0) + 1;
  }
}

/**
 * Records a retry for AI metrics
 */
recordRetry(project: RefactoringProject, phaseNumber: number, taskId: string): void {
  const task = this.findTask(project, phaseNumber, taskId);
  if (task?.aiMetrics) {
    task.aiMetrics.retryCount = (task.aiMetrics.retryCount || 0) + 1;
    task.aiMetrics.firstPassSuccess = false;
  }
}

/**
 * Records token usage
 */
recordTokens(
  project: RefactoringProject, 
  phaseNumber: number, 
  taskId: string,
  input: number,
  output: number
): void {
  const task = this.findTask(project, phaseNumber, taskId);
  if (task?.aiMetrics) {
    task.aiMetrics.inputTokens = (task.aiMetrics.inputTokens || 0) + input;
    task.aiMetrics.outputTokens = (task.aiMetrics.outputTokens || 0) + output;
    task.aiMetrics.totalTokens = task.aiMetrics.inputTokens + task.aiMetrics.outputTokens;
  }
}

private findTask(project: RefactoringProject, phaseNumber: number, taskId: string): TaskExecution | undefined {
  const phase = project.phases.find(p => p.phase === phaseNumber);
  return phase?.tasks.find(t => t.taskId === taskId);
}
```

**Verify:** `pnpm check && pnpm test`

---

### PHASE 5: Outcome Analyzer (~20 min)

**File:** `src/lib/refactoring/executor/OutcomeAnalyzer.ts`

#### Step 5.1: Update generateEstimationFeedback
Add AI-specific feedback generation in the loop:
```typescript
// Generate AI-specific feedback if AI metrics present
if (taskExecution.aiMetrics) {
  const aiMetrics = taskExecution.aiMetrics;
  const aiAccuracy = aiMetrics.actualMinutes 
    ? this.calculateEstimationAccuracy(
        aiMetrics.estimatedMinutes,
        aiMetrics.actualMinutes
      )
    : 0;
  
  feedback.push({
    id: `feedback-ai-${taskExecution.taskId}`,
    taskCategory: planTask.category,
    taskDescription: planTask.title,
    
    // Keep human fields for backward compat
    estimatedHours: planTask.estimatedHours,
    actualHours: (aiMetrics.actualMinutes || 0) / 60,
    accuracy: aiAccuracy,
    
    // AI-specific fields
    executorType: aiMetrics.executorType,
    estimatedMinutesAI: aiMetrics.estimatedMinutes,
    actualMinutesAI: aiMetrics.actualMinutes,
    accuracyAI: aiAccuracy,
    
    aiFactors: {
      codebaseSize: planTask.files?.length || 0,
      complexity: this.inferComplexity(planTask),
      hasTests: planTask.category === 'testing',
      requiresNewTests: (planTask.acceptance || []).some(a => 
        a.toLowerCase().includes('test')
      ),
      crossFileChanges: planTask.files?.length || 0,
      tokenIntensity: this.inferTokenIntensity(aiMetrics)
    },
    
    codebaseContext: {
      size: project.plan.phases.reduce((sum, p) => sum + p.tasks.length, 0),
      techStack: project.plan.standardsId,
      quality: 70
    },
    
    factors: this.identifyAIFactors(aiMetrics, planTask)
  });
}
```

#### Step 5.2: Add helper methods
```typescript
private inferComplexity(task: RefactoringTask): 'low' | 'medium' | 'high' {
  if (task.estimatedHours <= 1) return 'low';
  if (task.estimatedHours <= 4) return 'medium';
  return 'high';
}

private inferTokenIntensity(metrics: AIExecutionMetrics): 'low' | 'medium' | 'high' {
  const tokens = metrics.totalTokens || 0;
  if (tokens < 10000) return 'low';
  if (tokens < 50000) return 'medium';
  return 'high';
}

private identifyAIFactors(metrics: AIExecutionMetrics, task: RefactoringTask): string[] {
  const factors: string[] = [];
  
  if (!metrics.firstPassSuccess) {
    factors.push('Required retries');
  }
  if (metrics.iterationCount > 2) {
    factors.push(`Multiple iterations (${metrics.iterationCount})`);
  }
  if ((metrics.totalTokens || 0) > 50000) {
    factors.push('High token usage');
  }
  if (task.files?.length > 10) {
    factors.push('Many files affected');
  }
  
  return factors;
}
```

**Verify:** `pnpm check && pnpm test`

---

### PHASE 6: Learning Loop (~15 min)

**File:** `src/lib/refactoring/executor/LearningLoop.ts`

#### Step 6.1: Add AI-specific endpoint
```typescript
/**
 * Records AI execution feedback to NeuroForge
 */
async recordAIExecutionFeedback(feedback: EstimationFeedback[]): Promise<void> {
  const aiFeedback = feedback.filter(f => 
    f.executorType && f.executorType.startsWith('ai-')
  );
  
  if (!this.enabled || aiFeedback.length === 0) {
    return;
  }
  
  try {
    const response = await fetch(`${this.baseUrl}/learning/ai-execution-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback: aiFeedback })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to record AI feedback: ${response.statusText}`);
    }
    
    console.log(`[LearningLoop] Recorded ${aiFeedback.length} AI execution feedback entries`);
  } catch (error) {
    console.error('[LearningLoop] Error recording AI feedback:', error);
  }
}
```

#### Step 6.2: Update recordEstimationFeedback
After existing logic, add:
```typescript
// Also record AI-specific feedback if present
await this.recordAIExecutionFeedback(feedback);
```

**Verify:** `pnpm check && pnpm test`

---

### PHASE 7: Prompt Generator (~10 min)

**File:** `src/lib/refactoring/planner/PromptGenerator.ts`

#### Step 7.1: Update task prompt to show AI estimate
In `generateTaskPrompt`, update the Estimated Time section:
```typescript
## Estimated Execution Time
- **AI (Claude Code):** ~${task.estimatedMinutesAI} minutes
- **Human Developer:** ~${task.estimatedHours} hours

## AI Execution Notes
- Target first-pass success (complete without manual intervention)
- Run verification commands after each significant change
- Commit after each completed sub-task
```

**Verify:** `pnpm check && pnpm test`

---

### PHASE 8: Tests (~30 min)

Create test files for new functionality:

#### Step 8.1: EstimationEngine tests
**File:** `src/lib/refactoring/planner/EstimationEngine.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { EstimationEngine } from './EstimationEngine';

describe('EstimationEngine', () => {
  const engine = new EstimationEngine();
  
  describe('humanHoursToAIMinutes', () => {
    it('converts testing tasks with 8x multiplier', () => {
      expect(engine.humanHoursToAIMinutes(4, 'testing')).toBe(30);
    });
    
    it('converts type-safety tasks with 12x multiplier', () => {
      expect(engine.humanHoursToAIMinutes(2, 'type-safety')).toBe(10);
    });
    
    it('converts architecture tasks with 6x multiplier', () => {
      expect(engine.humanHoursToAIMinutes(6, 'architecture')).toBe(60);
    });
    
    it('uses 10x default for unknown categories', () => {
      expect(engine.humanHoursToAIMinutes(10, 'unknown' as any)).toBe(60);
    });
  });
  
  describe('formatAITime', () => {
    it('formats minutes under 60', () => {
      expect(engine.formatAITime(45)).toBe('45 min');
    });
    
    it('formats hours', () => {
      expect(engine.formatAITime(120)).toBe('2h');
    });
    
    it('formats hours and minutes', () => {
      expect(engine.formatAITime(90)).toBe('1h 30m');
    });
  });
  
  describe('refineAIEstimates', () => {
    it('uses learned estimate when confidence is high', () => {
      const tasks = [{
        id: '1',
        title: 'Test task',
        category: 'testing',
        estimatedHours: 4,
        estimatedMinutesAI: 30,
        aiEstimateConfidence: 0.3
      }];
      
      const recommendations = [{
        taskCategory: 'testing',
        taskPattern: 'Test task',
        suggestedEstimateHours: 3,
        confidence: 0.8,
        suggestedEstimateMinutesAI: 20,
        aiConfidence: 0.85
      }];
      
      const refined = engine.refineAIEstimates(tasks, recommendations);
      
      expect(refined[0].estimatedMinutesAI).toBe(20);
      expect(refined[0].aiEstimateConfidence).toBe(0.85);
    });
    
    it('falls back to derived estimate when no recommendation', () => {
      const tasks = [{
        id: '1',
        title: 'New task',
        category: 'testing',
        estimatedHours: 4,
        estimatedMinutesAI: 0,
        aiEstimateConfidence: 0
      }];
      
      const refined = engine.refineAIEstimates(tasks, []);
      
      expect(refined[0].estimatedMinutesAI).toBe(30); // 4h / 8x = 30min
      expect(refined[0].aiEstimateConfidence).toBe(0.3);
    });
  });
  
  describe('calculateTotalAIEstimate', () => {
    it('sums all AI estimates', () => {
      const tasks = [
        { estimatedMinutesAI: 30 },
        { estimatedMinutesAI: 20 },
        { estimatedMinutesAI: 15 }
      ];
      
      expect(engine.calculateTotalAIEstimate(tasks as any)).toBe(65);
    });
  });
});
```

**Verify:** `pnpm test:coverage` - ensure 100% coverage on new code

---

### FINAL: Verification

```bash
# Type check
pnpm check

# Run all tests
pnpm test

# Check coverage
pnpm test:coverage

# Build
pnpm build

# Commit
git add -A
git commit -m "feat: Add AI execution analytics and time tracking"
```

---

## Success Criteria

- [ ] All new types compile without errors
- [ ] EstimationEngine converts hours → minutes correctly
- [ ] TaskExecutor captures AI metrics during execution
- [ ] OutcomeAnalyzer generates AI-specific feedback
- [ ] LearningLoop records AI feedback to NeuroForge
- [ ] Prompt generator shows AI time estimates
- [ ] 100% test coverage on new code
- [ ] Backward compatible - existing human tracking works

---

Begin execution now. Start with Phase 1, Step 1.1.
```

---

# End of Document

**Created:** November 26, 2025  
**AI Execution Time:** 2-3 hours
