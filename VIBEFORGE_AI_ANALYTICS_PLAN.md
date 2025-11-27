# VibeForge AI Execution Analytics - Implementation Plan

**Version:** 1.0  
**Created:** November 26, 2025  
**AI Execution Time:** ~2-3 hours

---

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

## Implementation Tasks

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
```typescript
/**
 * Converts human hours to AI minutes
 * Based on empirical data: AI is ~10-15x faster for code tasks
 */
humanHoursToAIMinutes(humanHours: number, category: TaskCategory): number {
  const multipliers: Record<TaskCategory, number> = {
    'testing': 8,           // AI writes tests fast
    'type-safety': 12,      // Mechanical, AI excels
    'code-quality': 10,     // Refactoring is AI strength
    'architecture': 6,      // Requires more reasoning
    'documentation': 15,    // AI writes docs very fast
  };
  
  const multiplier = multipliers[category] || 10;
  return Math.round((humanHours * 60) / multiplier);
}

/**
 * Refines AI estimates from learning data
 */
refineAIEstimates(
  tasks: RefactoringTask[],
  recommendations: TaskRecommendation[]
): RefactoringTask[] {
  return tasks.map(task => {
    const rec = this.findMatchingRecommendation(task, recommendations);
    
    if (rec && rec.aiConfidence > 0.5) {
      return {
        ...task,
        estimatedMinutesAI: rec.suggestedEstimateMinutesAI,
        aiEstimateConfidence: rec.aiConfidence
      };
    }
    
    // Fallback: derive from human estimate
    return {
      ...task,
      estimatedMinutesAI: this.humanHoursToAIMinutes(
        task.estimatedHours, 
        task.category
      ),
      aiEstimateConfidence: 0.3  // Low confidence for derived
    };
  });
}
```

### Phase 3: Task Executor Updates (~30 min)

**File:** `src/lib/refactoring/executor/TaskExecutor.ts`

**Changes:**
1. Capture `executorType` at execution start
2. Track AI metrics during execution
3. Calculate AI-specific duration

```typescript
async executeTask(
  project: RefactoringProject,
  phaseNumber: number,
  taskId: string,
  executorType: ExecutorType = 'ai-claude-code'
): Promise<RefactoringProject> {
  // ... existing code ...
  
  // NEW: Initialize AI metrics
  if (executorType.startsWith('ai-')) {
    taskExecution.aiMetrics = {
      executorType,
      estimatedMinutes: planTask.estimatedMinutesAI,
      apiCalls: 0,
      retryCount: 0,
      iterationCount: 0,
      firstPassSuccess: true,
      testPassedOnFirst: true
    };
  }
  
  // ... execution logic ...
  
  // NEW: Capture AI metrics on completion
  if (taskExecution.aiMetrics) {
    const startTime = new Date(taskExecution.startedAt!).getTime();
    const endTime = new Date(taskExecution.completedAt!).getTime();
    taskExecution.aiMetrics.actualMinutes = (endTime - startTime) / 60000;
  }
  
  return project;
}
```

### Phase 4: Outcome Analyzer Updates (~20 min)

**File:** `src/lib/refactoring/executor/OutcomeAnalyzer.ts`

**Changes:**
1. Generate AI-specific feedback
2. Calculate AI accuracy separately

```typescript
generateEstimationFeedback(project: RefactoringProject): EstimationFeedback[] {
  const feedback: EstimationFeedback[] = [];
  
  for (const phase of project.phases) {
    for (const taskExecution of phase.tasks) {
      // ... existing human feedback code ...
      
      // NEW: AI-specific feedback
      if (taskExecution.aiMetrics) {
        const aiMetrics = taskExecution.aiMetrics;
        const aiAccuracy = this.calculateEstimationAccuracy(
          aiMetrics.estimatedMinutes,
          aiMetrics.actualMinutes || 0
        );
        
        feedback.push({
          id: `feedback-ai-${taskExecution.taskId}`,
          taskCategory: planTask.category,
          taskDescription: planTask.title,
          
          // Human fields (for compat)
          estimatedHours: planTask.estimatedHours,
          actualHours: (aiMetrics.actualMinutes || 0) / 60,
          accuracy: aiAccuracy,
          
          // AI-specific
          executorType: aiMetrics.executorType,
          estimatedMinutesAI: aiMetrics.estimatedMinutes,
          actualMinutesAI: aiMetrics.actualMinutes,
          accuracyAI: aiAccuracy,
          
          aiFactors: {
            codebaseSize: planTask.files.length,
            complexity: this.inferComplexity(planTask),
            hasTests: planTask.category === 'testing',
            requiresNewTests: planTask.acceptance.some(a => 
              a.toLowerCase().includes('test')
            ),
            crossFileChanges: planTask.files.length,
            tokenIntensity: this.inferTokenIntensity(planTask)
          },
          
          codebaseContext: { ... },
          factors: [ ... ]
        });
      }
    }
  }
  
  return feedback;
}
```

### Phase 5: Learning Loop Updates (~20 min)

**File:** `src/lib/refactoring/executor/LearningLoop.ts`

**Changes:**
1. Separate endpoints for AI vs human feedback
2. Request AI-specific recommendations

```typescript
/**
 * Records AI execution feedback to NeuroForge
 */
async recordAIExecutionFeedback(feedback: EstimationFeedback[]): Promise<void> {
  const aiFeedback = feedback.filter(f => f.executorType?.startsWith('ai-'));
  
  if (!this.enabled || aiFeedback.length === 0) return;
  
  try {
    const response = await fetch(`${this.baseUrl}/learning/ai-estimation-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback: aiFeedback })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to record AI feedback: ${response.statusText}`);
    }
    
    console.log(`[LearningLoop] Recorded ${aiFeedback.length} AI estimation entries`);
  } catch (error) {
    console.error('[LearningLoop] Error recording AI feedback:', error);
  }
}

/**
 * Gets AI-specific task recommendations
 */
async getAITaskRecommendations(
  request: RecommendationRequest
): Promise<TaskRecommendation[]> {
  // Request includes AI context
  const aiRequest = {
    ...request,
    executorType: 'ai-claude-code',
    includeAIEstimates: true
  };
  
  // ... fetch and return ...
}
```

### Phase 6: Analytics Dashboard Updates (~30 min)

**File:** `src/routes/analytics/+page.svelte` (new tab)

**New "AI Execution" tab showing:**
- Average AI execution time vs estimate
- Accuracy trend over time
- Task category breakdown (which tasks AI does fastest)
- Token usage per task type
- First-pass success rate
- Cost per task type

```svelte
<!-- AI Execution Analytics Tab -->
<div class="grid grid-cols-4 gap-4">
  <div class="stat-card">
    <h3>Avg AI Time</h3>
    <p class="text-2xl">{avgMinutes} min</p>
    <p class="text-xs text-slate-400">vs {avgEstimated} estimated</p>
  </div>
  
  <div class="stat-card">
    <h3>Estimation Accuracy</h3>
    <p class="text-2xl">{accuracy}%</p>
    <p class="text-xs text-slate-400">AI estimates</p>
  </div>
  
  <div class="stat-card">
    <h3>First-Pass Success</h3>
    <p class="text-2xl">{firstPassRate}%</p>
    <p class="text-xs text-slate-400">No intervention needed</p>
  </div>
  
  <div class="stat-card">
    <h3>Avg Cost/Task</h3>
    <p class="text-2xl">${avgCost}</p>
    <p class="text-xs text-slate-400">API + tokens</p>
  </div>
</div>

<!-- Task Type Breakdown -->
<div class="mt-6">
  <h3>AI Speed by Task Type</h3>
  {#each taskTypes as type}
    <div class="flex items-center gap-2">
      <span class="w-32">{type.name}</span>
      <div class="flex-1 bg-slate-700 rounded h-4">
        <div 
          class="bg-emerald-500 h-full rounded"
          style="width: {type.speedMultiplier * 10}%"
        />
      </div>
      <span>{type.speedMultiplier}x faster</span>
    </div>
  {/each}
</div>
```

### Phase 7: Prompt Generator Updates (~15 min)

**File:** `src/lib/refactoring/planner/PromptGenerator.ts`

**Changes:**
1. Show AI estimates in generated prompts
2. Add AI-specific instructions

```typescript
generateTaskPrompt(task: RefactoringTask, standards: QualityStandards): ClaudePromptDocument {
  const content = `# Refactoring Task: ${task.title}

## Objective
${task.description}

## Estimated Time
- **AI Execution:** ${task.estimatedMinutesAI} minutes
- **Human Reference:** ${task.estimatedHours} hours

## AI Execution Notes
- Target first-pass success (no manual intervention)
- Run verification commands after each file change
- Track iteration count for analytics

...
`;
  // ... rest of prompt
}
```

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

1. **Phase 1-2:** Update types and estimation engine (backward compatible)
2. **Phase 3-4:** Update executors with optional AI metrics
3. **Phase 5:** Add new learning endpoints (parallel to existing)
4. **Phase 6:** Add analytics tab (additive, no breaking changes)
5. **Phase 7:** Update prompts to show AI estimates

All changes are **additive** - existing human-oriented tracking continues to work.

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

## Next Steps

1. Implement Phase 1-4 (core types and tracking)
2. Run several refactoring sessions with Claude Code
3. Collect baseline AI execution data
4. Train estimation model on AI-specific data
5. Refine multipliers based on real data

---

**Document Version:** 1.0  
**Author:** Claude (VibeForge Architecture)
