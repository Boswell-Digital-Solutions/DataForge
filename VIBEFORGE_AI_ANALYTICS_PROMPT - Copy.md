# VibeForge AI Execution Analytics - Claude Code Prompt

**Version:** 1.0  
**Created:** November 26, 2025  
**Expected Duration:** 2-3 hours

---

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
});
```

#### Step 8.2: Add more tests for AI metrics tracking

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

**Document Version:** 1.0  
**Author:** Claude (VibeForge Architecture)
