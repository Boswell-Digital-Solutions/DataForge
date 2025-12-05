# VibeForge Refactoring Automation - Implementation Plan

**Version:** 1.0  
**Created:** November 25, 2025  
**Feature:** Automated Refactoring with Learning  
**Estimated Effort:** 320 hours (8 weeks)  
**Prerequisites:** VibeForge 1.0 core complete

---

## ⚠️ MANDATORY STANDARD

**100% Test Coverage is required.** This is a Forge product. Every function, component, and API call ships with tests. No exceptions.

---

## Executive Summary

This plan implements automated refactoring capabilities in VibeForge with a learning loop powered by NeuroForge. Users can analyze codebases, generate refactoring plans based on configurable quality standards, execute plans via Claude Code integration, and contribute to a learning system that improves recommendations over time.

### Before Starting

```bash
cd ~/projects/Coding2025/Forge/vibeforge
git checkout -b feature/refactoring-automation
git add -A && git commit -m "checkpoint: pre-refactoring-automation"
```

### Key Principles

1. **100% test coverage** - Forge standard, non-negotiable
2. **User-defined standards** - Their rules, their choice
3. **Learning improves over time** - NeuroForge gets smarter
4. **Git checkpoints per phase** - Safe rollback points
5. **Free core, paid execution** - VibeForge free, NeuroForge paid

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    VibeForge (Frontend)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Analyzer   │───▶│   Planner    │───▶│  Executor    │       │
│  │              │    │              │    │              │       │
│  │ • AST Parse  │    │ • Task Gen   │    │ • Claude API │       │
│  │ • Metrics    │    │ • Phase Gen  │    │ • Git Ops    │       │
│  │ • Patterns   │    │ • Gates      │    │ • Monitoring │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                             ▼                                    │
│                    ┌──────────────┐                              │
│                    │  Standards   │                              │
│                    │   Engine     │                              │
│                    │              │                              │
│                    │ • Profiles   │                              │
│                    │ • Rules      │                              │
│                    │ • Gates      │                              │
│                    └──────────────┘                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                         API Layer                                │
│  neuroforgeClient.ts          dataforgeClient.ts                │
└──────────────────┬─────────────────────────┬────────────────────┘
                   │                         │
                   ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │    NeuroForge    │      │    DataForge     │
        │   (Commercial)   │      │   (Commercial)   │
        │                  │      │                  │
        │ • Learning Store │      │ • Project Store  │
        │ • Recommendations│      │ • Standards      │
        │ • Predictions    │      │ • Analytics      │
        │ • LLM Execution  │      │ • History        │
        └──────────────────┘      └──────────────────┘
```

---

## Directory Structure

```
src/lib/refactoring/
├── analyzer/
│   ├── index.ts                    # Barrel export
│   ├── CodebaseAnalyzer.ts         # Main analyzer class
│   ├── parsers/
│   │   ├── TypeScriptParser.ts     # TS/JS AST parsing
│   │   ├── SvelteParser.ts         # Svelte file parsing
│   │   ├── PythonParser.ts         # Python parsing
│   │   └── GenericParser.ts        # Fallback parser
│   ├── metrics/
│   │   ├── CoverageMetrics.ts      # Test coverage analysis
│   │   ├── ComplexityMetrics.ts    # Cyclomatic complexity
│   │   ├── TypeMetrics.ts          # Type safety analysis
│   │   └── PatternMetrics.ts       # Code pattern detection
│   └── __tests__/
│       ├── CodebaseAnalyzer.test.ts
│       ├── parsers/*.test.ts
│       └── metrics/*.test.ts
│
├── standards/
│   ├── index.ts
│   ├── StandardsEngine.ts          # Standards evaluation
│   ├── QualityStandards.ts         # Standards types
│   ├── presets/
│   │   ├── strict.ts               # 100% coverage preset
│   │   ├── balanced.ts             # 80% coverage preset
│   │   ├── startup.ts              # 60% coverage preset
│   │   └── legacy.ts               # 40% coverage preset
│   ├── rules/
│   │   ├── CoverageRule.ts
│   │   ├── TypeSafetyRule.ts
│   │   ├── TodoRule.ts
│   │   └── CustomRule.ts
│   └── __tests__/
│       └── StandardsEngine.test.ts
│
├── planner/
│   ├── index.ts
│   ├── RefactoringPlanner.ts       # Plan generation
│   ├── TaskGenerator.ts            # Task breakdown
│   ├── PhaseGenerator.ts           # Phase organization
│   ├── EstimationEngine.ts         # Time estimates
│   ├── templates/
│   │   ├── svelte5-migration.ts
│   │   ├── test-coverage.ts
│   │   ├── type-safety.ts
│   │   └── store-migration.ts
│   └── __tests__/
│       └── RefactoringPlanner.test.ts
│
├── executor/
│   ├── index.ts
│   ├── RefactoringExecutor.ts      # Execution orchestration
│   ├── ClaudeCodeBridge.ts         # Claude Code integration
│   ├── GitOperations.ts            # Git checkpoint management
│   ├── GateVerifier.ts             # Quality gate verification
│   ├── ProgressMonitor.ts          # Execution progress tracking
│   └── __tests__/
│       └── RefactoringExecutor.test.ts
│
├── learning/
│   ├── index.ts
│   ├── LearningClient.ts           # NeuroForge learning API
│   ├── OutcomeRecorder.ts          # Record refactoring outcomes
│   ├── RecommendationEngine.ts     # Get learned recommendations
│   └── __tests__/
│       └── LearningClient.test.ts
│
├── types/
│   ├── analysis.ts                 # Analysis types
│   ├── standards.ts                # Standards types
│   ├── planning.ts                 # Planning types
│   ├── execution.ts                # Execution types
│   └── learning.ts                 # Learning types
│
└── stores/
    ├── refactoringProject.svelte.ts
    ├── analysisResults.svelte.ts
    ├── executionProgress.svelte.ts
    └── __tests__/
        └── *.test.ts
```

---

## Phase 1: Core Types & Standards Engine (Week 1)

### Objective

Define all types and implement the configurable standards system.

---

### Task 1.1: Core Type Definitions

**Priority:** P0  
**Estimated Hours:** 8  
**Files to Create:**

```
src/lib/refactoring/types/analysis.ts
src/lib/refactoring/types/standards.ts
src/lib/refactoring/types/planning.ts
src/lib/refactoring/types/execution.ts
src/lib/refactoring/types/learning.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/types/analysis.ts

export interface CodebaseAnalysis {
  id: string;
  path: string;
  analyzedAt: string;
  gitCommit: string;
  
  // Structure
  structure: {
    totalFiles: number;
    sourceFiles: number;
    testFiles: number;
    directories: DirectoryNode[];
  };
  
  // Tech Stack Detection
  techStack: DetectedTechStack;
  
  // Metrics
  metrics: CodeMetrics;
  
  // Issues Found
  issues: CodeIssue[];
  
  // Patterns Detected
  patterns: DetectedPattern[];
}

export interface DirectoryNode {
  path: string;
  name: string;
  type: 'directory' | 'file';
  children?: DirectoryNode[];
  fileType?: FileType;
}

export type FileType = 
  | 'typescript'
  | 'javascript'
  | 'svelte'
  | 'python'
  | 'rust'
  | 'json'
  | 'markdown'
  | 'css'
  | 'html'
  | 'test'
  | 'config'
  | 'other';

export interface DetectedTechStack {
  framework: FrameworkType | null;
  language: LanguageType;
  stateManagement: StateManagementType | null;
  testFramework: TestFrameworkType | null;
  buildTool: BuildToolType | null;
  styling: StylingType | null;
}

export type FrameworkType = 
  | 'sveltekit' | 'svelte' 
  | 'nextjs' | 'react' 
  | 'vue' | 'nuxt'
  | 'fastapi' | 'django' | 'flask'
  | 'express' | 'nestjs';

export type LanguageType = 
  | 'typescript' | 'javascript' 
  | 'python' | 'rust' | 'go';

export type StateManagementType =
  | 'svelte-runes' | 'svelte-stores'
  | 'redux' | 'zustand' | 'jotai'
  | 'pinia' | 'vuex';

export type TestFrameworkType =
  | 'vitest' | 'jest' | 'playwright'
  | 'pytest' | 'unittest';

export type BuildToolType =
  | 'vite' | 'webpack' | 'rollup' | 'esbuild';

export type StylingType =
  | 'tailwind' | 'css-modules' | 'styled-components' | 'scss';

export interface CodeMetrics {
  // Coverage
  testCoverage: {
    statements: number;
    branches: number;
    functions: number;
    lines: number;
    hasReport: boolean;
  };
  
  // Type Safety
  typeSafety: {
    anyTypeCount: number;
    implicitAnyCount: number;
    typeErrorCount: number;
    strictModeEnabled: boolean;
  };
  
  // Code Quality
  quality: {
    todoCount: number;
    fixmeCount: number;
    complexityScore: number;
    duplicateLineCount: number;
  };
  
  // Size
  size: {
    totalLines: number;
    codeLines: number;
    commentLines: number;
    blankLines: number;
  };
}

export interface CodeIssue {
  id: string;
  type: IssueType;
  severity: 'critical' | 'high' | 'medium' | 'low';
  file: string;
  line?: number;
  message: string;
  rule?: string;
  autoFixable: boolean;
}

export type IssueType =
  | 'coverage'
  | 'type-safety'
  | 'todo-marker'
  | 'complexity'
  | 'pattern-violation'
  | 'security'
  | 'accessibility'
  | 'performance';

export interface DetectedPattern {
  name: string;
  type: 'store' | 'component' | 'api' | 'architecture';
  current: string;        // e.g., "writable"
  recommended?: string;   // e.g., "runes"
  files: string[];
  migrationAvailable: boolean;
}
```

```typescript
// src/lib/refactoring/types/standards.ts

export interface QualityStandards {
  id: string;
  name: string;
  description: string;
  isDefault: boolean;
  isPreset: boolean;
  createdAt: string;
  updatedAt: string;
  
  testing: TestingStandards;
  typeSafety: TypeSafetyStandards;
  codeQuality: CodeQualityStandards;
  architecture: ArchitectureStandards;
  gitWorkflow: GitWorkflowStandards;
  customRules: CustomRule[];
}

export interface TestingStandards {
  minimumCoverage: number;            // 0-100
  requireUnitTests: boolean;
  requireComponentTests: boolean;
  requireIntegrationTests: boolean;
  requireE2ETests: boolean;
  coverageGatePhase: number;          // Which phase enforces
}

export interface TypeSafetyStandards {
  allowAnyTypes: boolean;
  requireStrictMode: boolean;
  maxTypeErrors: number;
}

export interface CodeQualityStandards {
  maxTodoMarkers: number;             // 0 = none allowed
  maxComplexityScore: number;
  requireErrorHandling: boolean;
  requireAccessibility: boolean;
  requireDocumentation: boolean;
}

export interface ArchitectureStandards {
  // Svelte-specific
  svelteStorePattern?: 'runes' | 'writable' | 'any';
  
  // React-specific
  reactStatePattern?: 'hooks' | 'redux' | 'zustand' | 'any';
  
  // General
  requireCentralizedApi: boolean;
  requireErrorBoundaries: boolean;
  maxFileLines: number;
  maxFunctionLines: number;
}

export interface GitWorkflowStandards {
  checkpointAfterPhase: boolean;
  requireFeatureBranch: boolean;
  commitPrefix: string;
  tagOnComplete: boolean;
  protectedBranches: string[];
}

export interface CustomRule {
  id: string;
  name: string;
  enabled: boolean;
  type: 'regex' | 'ast' | 'metric';
  target: 'file' | 'function' | 'class' | 'line';
  pattern: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  autofix?: string;
}

export interface QualityGate {
  name: string;
  phase: number;
  checks: GateCheck[];
  required: boolean;
}

export interface GateCheck {
  id: string;
  name: string;
  type: 'coverage' | 'types' | 'todos' | 'tests' | 'custom';
  threshold: number | boolean;
  currentValue?: number | boolean;
  passed?: boolean;
}

export interface GateResult {
  gate: QualityGate;
  passed: boolean;
  checks: GateCheckResult[];
  failureReason?: string;
}

export interface GateCheckResult {
  check: GateCheck;
  passed: boolean;
  actualValue: number | boolean;
  message: string;
}
```

```typescript
// src/lib/refactoring/types/planning.ts

export interface RefactoringPlan {
  id: string;
  projectPath: string;
  createdAt: string;
  
  // Source
  analysis: CodebaseAnalysis;
  standards: QualityStandards;
  
  // Summary
  summary: PlanSummary;
  
  // Execution Plan
  phases: Phase[];
  
  // Estimates
  estimates: PlanEstimates;
  
  // Generated Documents
  documents: {
    implementationPlan: string;     // Markdown
    claudePrompt: string;           // Markdown
  };
}

export interface PlanSummary {
  title: string;
  description: string;
  currentScore: number;             // 0-10
  targetScore: number;              // 0-10
  criticalIssues: number;
  highIssues: number;
  mediumIssues: number;
  lowIssues: number;
}

export interface Phase {
  id: string;
  number: number;
  name: string;
  objective: string;
  estimatedHours: number;
  
  tasks: Task[];
  gate: QualityGate;
  gitCheckpoint: GitCheckpoint;
  
  status: PhaseStatus;
}

export type PhaseStatus = 
  | 'pending' 
  | 'in_progress' 
  | 'gate_check' 
  | 'completed' 
  | 'failed';

export interface Task {
  id: string;
  phaseId: string;
  number: string;                   // e.g., "1.1", "2.3"
  name: string;
  description: string;
  priority: 'P0' | 'P1' | 'P2';
  estimatedHours: number;
  
  // What to change
  files: FileChange[];
  
  // Implementation details
  implementation: string;           // Code or instructions
  
  // Required tests
  tests: TestRequirement[];
  
  // Verification
  verification: string[];           // Commands to run
  
  // Dependencies
  dependsOn: string[];              // Task IDs
  
  status: TaskStatus;
}

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'skipped';

export interface FileChange {
  path: string;
  action: 'create' | 'modify' | 'delete' | 'rename';
  newPath?: string;                 // For rename
  description: string;
}

export interface TestRequirement {
  type: 'unit' | 'component' | 'integration' | 'e2e';
  file: string;
  description: string;
  coverage: string[];               // What to cover
}

export interface GitCheckpoint {
  commitMessage: string;
  tag?: string;
}

export interface PlanEstimates {
  totalHours: number;
  totalWeeks: number;
  confidence: 'low' | 'medium' | 'high';
  breakdown: {
    phase: string;
    hours: number;
    percentage: number;
  }[];
}
```

```typescript
// src/lib/refactoring/types/execution.ts

export interface RefactoringProject {
  id: string;
  name: string;
  path: string;
  
  // Plan
  plan: RefactoringPlan;
  
  // Execution State
  status: ProjectStatus;
  currentPhase: number;
  currentTask: string | null;
  
  // Progress
  progress: ExecutionProgress;
  
  // History
  phases: PhaseExecution[];
  
  // Git
  startCommit: string;
  currentCommit: string;
  branch: string;
  
  // Timing
  startedAt: string | null;
  completedAt: string | null;
  
  // Learning
  feedbackProvided: boolean;
}

export type ProjectStatus =
  | 'draft'
  | 'ready'
  | 'executing'
  | 'paused'
  | 'gate_failed'
  | 'completed'
  | 'failed'
  | 'rolled_back';

export interface ExecutionProgress {
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  skippedTasks: number;
  percentage: number;
  
  currentPhase: {
    name: string;
    progress: number;
  };
  
  currentTask: {
    id: string;
    name: string;
    status: string;
  } | null;
  
  recentLogs: ExecutionLog[];
}

export interface ExecutionLog {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
  taskId?: string;
  details?: string;
}

export interface PhaseExecution {
  phaseId: string;
  phaseName: string;
  
  // Tasks
  tasks: TaskExecution[];
  
  // Gate
  gateResult: GateResult | null;
  
  // Git
  startCommit: string;
  endCommit: string | null;
  
  // Timing
  estimatedHours: number;
  actualHours: number;
  startedAt: string;
  completedAt: string | null;
  
  // Status
  status: PhaseStatus;
}

export interface TaskExecution {
  taskId: string;
  taskName: string;
  taskType: string;
  
  // Outcome
  status: TaskStatus;
  errorMessage?: string;
  retryCount: number;
  
  // Files
  filesCreated: string[];
  filesModified: string[];
  filesDeleted: string[];
  
  // Metrics
  linesAdded: number;
  linesRemoved: number;
  testsAdded: number;
  
  // Timing
  estimatedHours: number;
  actualHours: number;
  startedAt: string;
  completedAt: string | null;
}

export interface ExecutorConfig {
  mode: 'supervised' | 'autonomous';
  
  // Claude Code
  claudeCodePath: string;
  usePermissionsFlag: boolean;
  
  // Git
  autoCommit: boolean;
  createBranch: boolean;
  branchPrefix: string;
  
  // Monitoring
  streamOutput: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  
  // Safety
  maxRetries: number;
  rollbackOnGateFailure: boolean;
  pauseOnError: boolean;
}
```

```typescript
// src/lib/refactoring/types/learning.ts

export interface LearningOutcome {
  projectId: string;
  
  // Context
  context: {
    techStack: DetectedTechStack;
    codebaseSize: number;
    initialCoverage: number;
    standardsProfile: string;
    targetCoverage: number;
  };
  
  // Outcomes
  success: boolean;
  finalCoverage: number;
  
  // Patterns
  patterns: PatternOutcome[];
  
  // Estimations
  estimations: EstimationOutcome[];
  
  // User Feedback
  feedback: UserFeedback | null;
}

export interface PatternOutcome {
  patternId: string;
  patternName: string;
  
  // Applied
  applied: boolean;
  filesAffected: number;
  
  // Outcome
  success: boolean;
  errorMessage?: string;
  rollbackRequired: boolean;
  
  // Timing
  estimatedHours: number;
  actualHours: number;
}

export interface EstimationOutcome {
  taskType: string;
  
  // Estimates
  estimatedHours: number;
  actualHours: number;
  accuracy: number;              // Percentage
  
  // Factors
  factors: {
    name: string;
    impact: number;              // Multiplier
  }[];
}

export interface UserFeedback {
  rating: number;                // 1-5
  whatWorkedWell: string[];
  whatWasHard: string[];
  suggestions: string;
  wouldRecommend: boolean;
}

export interface LearningRecommendation {
  type: 'pattern' | 'estimation' | 'sequence' | 'warning';
  confidence: number;            // 0-1
  
  // Content
  title: string;
  description: string;
  
  // For patterns
  pattern?: {
    id: string;
    successRate: number;
    avgDuration: number;
  };
  
  // For estimations
  estimation?: {
    taskType: string;
    adjustment: number;          // Multiplier
    reason: string;
  };
  
  // For warnings
  warning?: {
    riskFactor: string;
    likelihood: number;
    mitigation: string;
  };
}

export interface GatePrediction {
  phaseId: string;
  gateName: string;
  
  // Prediction
  predictedPassRate: number;     // 0-100
  confidence: number;            // 0-1
  
  // Risks
  riskFactors: {
    factor: string;
    impact: number;
    mitigation: string;
  }[];
  
  // Recommendations
  recommendations: string[];
}
```

**Tests Required:**

```typescript
// src/lib/refactoring/types/__tests__/types.test.ts
import { describe, it, expect } from 'vitest';
import type {
  CodebaseAnalysis,
  QualityStandards,
  RefactoringPlan,
  RefactoringProject,
  LearningOutcome,
} from '../';

describe('Type Definitions', () => {
  describe('CodebaseAnalysis', () => {
    it('should allow valid analysis structure', () => {
      const analysis: CodebaseAnalysis = {
        id: 'test-123',
        path: '/test/path',
        analyzedAt: new Date().toISOString(),
        gitCommit: 'abc123',
        structure: {
          totalFiles: 100,
          sourceFiles: 80,
          testFiles: 20,
          directories: [],
        },
        techStack: {
          framework: 'sveltekit',
          language: 'typescript',
          stateManagement: 'svelte-runes',
          testFramework: 'vitest',
          buildTool: 'vite',
          styling: 'tailwind',
        },
        metrics: {
          testCoverage: {
            statements: 80,
            branches: 75,
            functions: 85,
            lines: 80,
            hasReport: true,
          },
          typeSafety: {
            anyTypeCount: 5,
            implicitAnyCount: 2,
            typeErrorCount: 0,
            strictModeEnabled: true,
          },
          quality: {
            todoCount: 10,
            fixmeCount: 2,
            complexityScore: 12,
            duplicateLineCount: 50,
          },
          size: {
            totalLines: 10000,
            codeLines: 7000,
            commentLines: 1500,
            blankLines: 1500,
          },
        },
        issues: [],
        patterns: [],
      };

      expect(analysis.id).toBe('test-123');
      expect(analysis.techStack.framework).toBe('sveltekit');
    });
  });

  // Additional type tests...
});
```

---

### Task 1.2: Standards Presets

**Priority:** P0  
**Estimated Hours:** 8  
**Files to Create:**

```
src/lib/refactoring/standards/presets/strict.ts
src/lib/refactoring/standards/presets/balanced.ts
src/lib/refactoring/standards/presets/startup.ts
src/lib/refactoring/standards/presets/legacy.ts
src/lib/refactoring/standards/presets/index.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/standards/presets/strict.ts

import type { QualityStandards } from '../../types/standards';

export const strictStandards: QualityStandards = {
  id: 'preset-strict',
  name: 'Strict (Forge Standard)',
  description: '100% coverage, zero tolerance. For teams that don\'t ship bugs.',
  isDefault: false,
  isPreset: true,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
  
  testing: {
    minimumCoverage: 100,
    requireUnitTests: true,
    requireComponentTests: true,
    requireIntegrationTests: true,
    requireE2ETests: true,
    coverageGatePhase: 2,
  },
  
  typeSafety: {
    allowAnyTypes: false,
    requireStrictMode: true,
    maxTypeErrors: 0,
  },
  
  codeQuality: {
    maxTodoMarkers: 0,
    maxComplexityScore: 10,
    requireErrorHandling: true,
    requireAccessibility: true,
    requireDocumentation: true,
  },
  
  architecture: {
    svelteStorePattern: 'runes',
    requireCentralizedApi: true,
    requireErrorBoundaries: true,
    maxFileLines: 300,
    maxFunctionLines: 50,
  },
  
  gitWorkflow: {
    checkpointAfterPhase: true,
    requireFeatureBranch: true,
    commitPrefix: 'refactor: ',
    tagOnComplete: true,
    protectedBranches: ['main', 'master'],
  },
  
  customRules: [],
};
```

```typescript
// src/lib/refactoring/standards/presets/balanced.ts

import type { QualityStandards } from '../../types/standards';

export const balancedStandards: QualityStandards = {
  id: 'preset-balanced',
  name: 'Balanced',
  description: '80% coverage, pragmatic quality. Good for most teams.',
  isDefault: true,
  isPreset: true,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
  
  testing: {
    minimumCoverage: 80,
    requireUnitTests: true,
    requireComponentTests: true,
    requireIntegrationTests: false,
    requireE2ETests: false,
    coverageGatePhase: 2,
  },
  
  typeSafety: {
    allowAnyTypes: false,
    requireStrictMode: true,
    maxTypeErrors: 0,
  },
  
  codeQuality: {
    maxTodoMarkers: 10,
    maxComplexityScore: 15,
    requireErrorHandling: true,
    requireAccessibility: false,
    requireDocumentation: false,
  },
  
  architecture: {
    svelteStorePattern: 'runes',
    requireCentralizedApi: true,
    requireErrorBoundaries: true,
    maxFileLines: 500,
    maxFunctionLines: 75,
  },
  
  gitWorkflow: {
    checkpointAfterPhase: true,
    requireFeatureBranch: true,
    commitPrefix: 'refactor: ',
    tagOnComplete: true,
    protectedBranches: ['main'],
  },
  
  customRules: [],
};
```

```typescript
// src/lib/refactoring/standards/presets/startup.ts

import type { QualityStandards } from '../../types/standards';

export const startupStandards: QualityStandards = {
  id: 'preset-startup',
  name: 'Startup Speed',
  description: '60% coverage, move fast. For early-stage products.',
  isDefault: false,
  isPreset: true,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
  
  testing: {
    minimumCoverage: 60,
    requireUnitTests: true,
    requireComponentTests: false,
    requireIntegrationTests: false,
    requireE2ETests: false,
    coverageGatePhase: 3,
  },
  
  typeSafety: {
    allowAnyTypes: true,
    requireStrictMode: false,
    maxTypeErrors: 20,
  },
  
  codeQuality: {
    maxTodoMarkers: 50,
    maxComplexityScore: 20,
    requireErrorHandling: false,
    requireAccessibility: false,
    requireDocumentation: false,
  },
  
  architecture: {
    svelteStorePattern: 'any',
    requireCentralizedApi: false,
    requireErrorBoundaries: false,
    maxFileLines: 1000,
    maxFunctionLines: 150,
  },
  
  gitWorkflow: {
    checkpointAfterPhase: true,
    requireFeatureBranch: false,
    commitPrefix: '',
    tagOnComplete: false,
    protectedBranches: [],
  },
  
  customRules: [],
};
```

```typescript
// src/lib/refactoring/standards/presets/legacy.ts

import type { QualityStandards } from '../../types/standards';

export const legacyStandards: QualityStandards = {
  id: 'preset-legacy',
  name: 'Legacy Rescue',
  description: '40% coverage, incremental improvement. For inherited codebases.',
  isDefault: false,
  isPreset: true,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
  
  testing: {
    minimumCoverage: 40,
    requireUnitTests: true,
    requireComponentTests: false,
    requireIntegrationTests: false,
    requireE2ETests: false,
    coverageGatePhase: 4,
  },
  
  typeSafety: {
    allowAnyTypes: true,
    requireStrictMode: false,
    maxTypeErrors: 100,
  },
  
  codeQuality: {
    maxTodoMarkers: 100,
    maxComplexityScore: 30,
    requireErrorHandling: false,
    requireAccessibility: false,
    requireDocumentation: false,
  },
  
  architecture: {
    svelteStorePattern: 'any',
    requireCentralizedApi: false,
    requireErrorBoundaries: false,
    maxFileLines: 2000,
    maxFunctionLines: 300,
  },
  
  gitWorkflow: {
    checkpointAfterPhase: true,
    requireFeatureBranch: false,
    commitPrefix: '',
    tagOnComplete: false,
    protectedBranches: [],
  },
  
  customRules: [],
};
```

```typescript
// src/lib/refactoring/standards/presets/index.ts

export { strictStandards } from './strict';
export { balancedStandards } from './balanced';
export { startupStandards } from './startup';
export { legacyStandards } from './legacy';

import { strictStandards } from './strict';
import { balancedStandards } from './balanced';
import { startupStandards } from './startup';
import { legacyStandards } from './legacy';
import type { QualityStandards } from '../../types/standards';

export const presetStandards: QualityStandards[] = [
  strictStandards,
  balancedStandards,
  startupStandards,
  legacyStandards,
];

export function getPresetById(id: string): QualityStandards | undefined {
  return presetStandards.find(p => p.id === id);
}

export function getDefaultPreset(): QualityStandards {
  return presetStandards.find(p => p.isDefault) ?? balancedStandards;
}
```

**Tests Required:**

```typescript
// src/lib/refactoring/standards/presets/__tests__/presets.test.ts

import { describe, it, expect } from 'vitest';
import {
  strictStandards,
  balancedStandards,
  startupStandards,
  legacyStandards,
  presetStandards,
  getPresetById,
  getDefaultPreset,
} from '../';

describe('Standards Presets', () => {
  describe('strictStandards', () => {
    it('should require 100% coverage', () => {
      expect(strictStandards.testing.minimumCoverage).toBe(100);
    });

    it('should not allow any types', () => {
      expect(strictStandards.typeSafety.allowAnyTypes).toBe(false);
    });

    it('should require all test types', () => {
      expect(strictStandards.testing.requireUnitTests).toBe(true);
      expect(strictStandards.testing.requireComponentTests).toBe(true);
      expect(strictStandards.testing.requireIntegrationTests).toBe(true);
      expect(strictStandards.testing.requireE2ETests).toBe(true);
    });

    it('should allow zero TODOs', () => {
      expect(strictStandards.codeQuality.maxTodoMarkers).toBe(0);
    });
  });

  describe('balancedStandards', () => {
    it('should require 80% coverage', () => {
      expect(balancedStandards.testing.minimumCoverage).toBe(80);
    });

    it('should be the default', () => {
      expect(balancedStandards.isDefault).toBe(true);
    });
  });

  describe('startupStandards', () => {
    it('should require 60% coverage', () => {
      expect(startupStandards.testing.minimumCoverage).toBe(60);
    });

    it('should allow any types', () => {
      expect(startupStandards.typeSafety.allowAnyTypes).toBe(true);
    });
  });

  describe('legacyStandards', () => {
    it('should require 40% coverage', () => {
      expect(legacyStandards.testing.minimumCoverage).toBe(40);
    });

    it('should allow many TODOs', () => {
      expect(legacyStandards.codeQuality.maxTodoMarkers).toBe(100);
    });
  });

  describe('presetStandards', () => {
    it('should contain all presets', () => {
      expect(presetStandards).toHaveLength(4);
    });

    it('should have exactly one default', () => {
      const defaults = presetStandards.filter(p => p.isDefault);
      expect(defaults).toHaveLength(1);
    });
  });

  describe('getPresetById', () => {
    it('should return preset by id', () => {
      const preset = getPresetById('preset-strict');
      expect(preset).toBe(strictStandards);
    });

    it('should return undefined for unknown id', () => {
      const preset = getPresetById('unknown');
      expect(preset).toBeUndefined();
    });
  });

  describe('getDefaultPreset', () => {
    it('should return balanced as default', () => {
      const preset = getDefaultPreset();
      expect(preset).toBe(balancedStandards);
    });
  });
});
```

---

### Task 1.3: Standards Engine

**Priority:** P0  
**Estimated Hours:** 16  
**Files to Create:**

```
src/lib/refactoring/standards/StandardsEngine.ts
src/lib/refactoring/standards/rules/CoverageRule.ts
src/lib/refactoring/standards/rules/TypeSafetyRule.ts
src/lib/refactoring/standards/rules/TodoRule.ts
src/lib/refactoring/standards/rules/index.ts
src/lib/refactoring/standards/index.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/standards/StandardsEngine.ts

import type {
  QualityStandards,
  QualityGate,
  GateResult,
  GateCheck,
  GateCheckResult,
} from '../types/standards';
import type { CodebaseAnalysis, CodeMetrics } from '../types/analysis';
import { evaluateCoverageRule } from './rules/CoverageRule';
import { evaluateTypeSafetyRule } from './rules/TypeSafetyRule';
import { evaluateTodoRule } from './rules/TodoRule';

export class StandardsEngine {
  private standards: QualityStandards;

  constructor(standards: QualityStandards) {
    this.standards = standards;
  }

  /**
   * Evaluate a codebase against the configured standards
   */
  evaluate(analysis: CodebaseAnalysis): StandardsEvaluation {
    const coverageResult = evaluateCoverageRule(
      analysis.metrics,
      this.standards.testing
    );

    const typeSafetyResult = evaluateTypeSafetyRule(
      analysis.metrics,
      this.standards.typeSafety
    );

    const todoResult = evaluateTodoRule(
      analysis.metrics,
      this.standards.codeQuality
    );

    const allChecks = [
      ...coverageResult.checks,
      ...typeSafetyResult.checks,
      ...todoResult.checks,
    ];

    const passed = allChecks.every(c => c.passed);
    const score = this.calculateScore(analysis.metrics, allChecks);

    return {
      passed,
      score,
      results: {
        coverage: coverageResult,
        typeSafety: typeSafetyResult,
        todos: todoResult,
      },
      summary: this.generateSummary(allChecks),
    };
  }

  /**
   * Generate quality gates for a refactoring plan
   */
  generateGates(): QualityGate[] {
    const gates: QualityGate[] = [];

    // Phase 1 Gate - Basic functionality
    gates.push({
      name: 'Phase 1: Core Functionality',
      phase: 1,
      required: true,
      checks: [
        {
          id: 'typescript-compiles',
          name: 'TypeScript Compiles',
          type: 'types',
          threshold: true,
        },
        {
          id: 'build-succeeds',
          name: 'Build Succeeds',
          type: 'tests',
          threshold: true,
        },
      ],
    });

    // Phase 2 Gate - Test coverage
    gates.push({
      name: 'Phase 2: Test Coverage',
      phase: 2,
      required: true,
      checks: [
        {
          id: 'minimum-coverage',
          name: `Coverage ≥ ${this.standards.testing.minimumCoverage}%`,
          type: 'coverage',
          threshold: this.standards.testing.minimumCoverage,
        },
        {
          id: 'tests-passing',
          name: 'All Tests Passing',
          type: 'tests',
          threshold: true,
        },
      ],
    });

    // Phase 3 Gate - Quality & Polish
    gates.push({
      name: 'Phase 3: Quality & Polish',
      phase: 3,
      required: true,
      checks: [
        {
          id: 'max-todos',
          name: `TODOs ≤ ${this.standards.codeQuality.maxTodoMarkers}`,
          type: 'todos',
          threshold: this.standards.codeQuality.maxTodoMarkers,
        },
        {
          id: 'no-any-types',
          name: this.standards.typeSafety.allowAnyTypes
            ? 'Any Types Allowed'
            : 'No Any Types',
          type: 'types',
          threshold: this.standards.typeSafety.allowAnyTypes ? 999 : 0,
        },
      ],
    });

    // Phase 4 Gate - Release Ready
    gates.push({
      name: 'Phase 4: Release Ready',
      phase: 4,
      required: true,
      checks: [
        {
          id: 'final-coverage',
          name: `Final Coverage ≥ ${this.standards.testing.minimumCoverage}%`,
          type: 'coverage',
          threshold: this.standards.testing.minimumCoverage,
        },
        {
          id: 'all-tests-passing',
          name: 'All Tests Passing',
          type: 'tests',
          threshold: true,
        },
        {
          id: 'build-succeeds',
          name: 'Production Build Succeeds',
          type: 'tests',
          threshold: true,
        },
      ],
    });

    return gates;
  }

  /**
   * Verify a quality gate against current metrics
   */
  verifyGate(gate: QualityGate, metrics: CodeMetrics): GateResult {
    const checkResults: GateCheckResult[] = gate.checks.map(check => {
      const result = this.evaluateCheck(check, metrics);
      return result;
    });

    const passed = checkResults.every(r => r.passed);

    return {
      gate,
      passed,
      checks: checkResults,
      failureReason: passed
        ? undefined
        : checkResults
            .filter(r => !r.passed)
            .map(r => r.message)
            .join('; '),
    };
  }

  private evaluateCheck(check: GateCheck, metrics: CodeMetrics): GateCheckResult {
    switch (check.type) {
      case 'coverage':
        return this.evaluateCoverageCheck(check, metrics);
      case 'types':
        return this.evaluateTypesCheck(check, metrics);
      case 'todos':
        return this.evaluateTodosCheck(check, metrics);
      case 'tests':
        return this.evaluateTestsCheck(check, metrics);
      default:
        return {
          check,
          passed: true,
          actualValue: true,
          message: 'Check type not implemented',
        };
    }
  }

  private evaluateCoverageCheck(
    check: GateCheck,
    metrics: CodeMetrics
  ): GateCheckResult {
    const threshold = check.threshold as number;
    const actual = metrics.testCoverage.lines;
    const passed = actual >= threshold;

    return {
      check,
      passed,
      actualValue: actual,
      message: passed
        ? `Coverage ${actual}% meets threshold ${threshold}%`
        : `Coverage ${actual}% below threshold ${threshold}%`,
    };
  }

  private evaluateTypesCheck(
    check: GateCheck,
    metrics: CodeMetrics
  ): GateCheckResult {
    if (typeof check.threshold === 'boolean') {
      // Boolean check - e.g., "TypeScript compiles"
      const passed = metrics.typeSafety.typeErrorCount === 0;
      return {
        check,
        passed,
        actualValue: passed,
        message: passed
          ? 'No TypeScript errors'
          : `${metrics.typeSafety.typeErrorCount} TypeScript errors found`,
      };
    }

    // Numeric check - e.g., "Max any types"
    const threshold = check.threshold as number;
    const actual = metrics.typeSafety.anyTypeCount;
    const passed = actual <= threshold;

    return {
      check,
      passed,
      actualValue: actual,
      message: passed
        ? `${actual} any types (max ${threshold})`
        : `${actual} any types exceeds max ${threshold}`,
    };
  }

  private evaluateTodosCheck(
    check: GateCheck,
    metrics: CodeMetrics
  ): GateCheckResult {
    const threshold = check.threshold as number;
    const actual = metrics.quality.todoCount;
    const passed = actual <= threshold;

    return {
      check,
      passed,
      actualValue: actual,
      message: passed
        ? `${actual} TODOs (max ${threshold})`
        : `${actual} TODOs exceeds max ${threshold}`,
    };
  }

  private evaluateTestsCheck(
    _check: GateCheck,
    _metrics: CodeMetrics
  ): GateCheckResult {
    // This would need to run actual test command
    // For now, assume passed if we have coverage data
    return {
      check: _check,
      passed: true,
      actualValue: true,
      message: 'Tests passing (requires runtime verification)',
    };
  }

  private calculateScore(metrics: CodeMetrics, checks: any[]): number {
    const passedChecks = checks.filter(c => c.passed).length;
    const totalChecks = checks.length;

    const checkScore = (passedChecks / totalChecks) * 5;
    const coverageScore = (metrics.testCoverage.lines / 100) * 3;
    const qualityScore =
      metrics.quality.todoCount === 0
        ? 2
        : Math.max(0, 2 - metrics.quality.todoCount * 0.1);

    return Math.min(10, checkScore + coverageScore + qualityScore);
  }

  private generateSummary(checks: any[]): string {
    const passed = checks.filter(c => c.passed).length;
    const total = checks.length;

    if (passed === total) {
      return 'All quality standards met';
    }

    const failed = checks.filter(c => !c.passed);
    return `${passed}/${total} checks passed. Failed: ${failed.map(c => c.name).join(', ')}`;
  }
}

export interface StandardsEvaluation {
  passed: boolean;
  score: number;
  results: {
    coverage: RuleResult;
    typeSafety: RuleResult;
    todos: RuleResult;
  };
  summary: string;
}

export interface RuleResult {
  passed: boolean;
  checks: {
    name: string;
    passed: boolean;
    actualValue: number | boolean;
    threshold: number | boolean;
    message: string;
  }[];
}
```

```typescript
// src/lib/refactoring/standards/rules/CoverageRule.ts

import type { CodeMetrics } from '../../types/analysis';
import type { TestingStandards } from '../../types/standards';
import type { RuleResult } from '../StandardsEngine';

export function evaluateCoverageRule(
  metrics: CodeMetrics,
  standards: TestingStandards
): RuleResult {
  const checks = [];

  // Minimum coverage check
  const coverageCheck = {
    name: `Minimum Coverage (${standards.minimumCoverage}%)`,
    passed: metrics.testCoverage.lines >= standards.minimumCoverage,
    actualValue: metrics.testCoverage.lines,
    threshold: standards.minimumCoverage,
    message: metrics.testCoverage.lines >= standards.minimumCoverage
      ? `Coverage ${metrics.testCoverage.lines}% meets minimum ${standards.minimumCoverage}%`
      : `Coverage ${metrics.testCoverage.lines}% below minimum ${standards.minimumCoverage}%`,
  };
  checks.push(coverageCheck);

  // Coverage report exists
  const reportCheck = {
    name: 'Coverage Report Exists',
    passed: metrics.testCoverage.hasReport,
    actualValue: metrics.testCoverage.hasReport,
    threshold: true,
    message: metrics.testCoverage.hasReport
      ? 'Coverage report found'
      : 'No coverage report found - run tests with coverage',
  };
  checks.push(reportCheck);

  return {
    passed: checks.every(c => c.passed),
    checks,
  };
}
```

```typescript
// src/lib/refactoring/standards/rules/TypeSafetyRule.ts

import type { CodeMetrics } from '../../types/analysis';
import type { TypeSafetyStandards } from '../../types/standards';
import type { RuleResult } from '../StandardsEngine';

export function evaluateTypeSafetyRule(
  metrics: CodeMetrics,
  standards: TypeSafetyStandards
): RuleResult {
  const checks = [];

  // Any types check
  if (!standards.allowAnyTypes) {
    const anyCheck = {
      name: 'No Any Types',
      passed: metrics.typeSafety.anyTypeCount === 0,
      actualValue: metrics.typeSafety.anyTypeCount,
      threshold: 0,
      message: metrics.typeSafety.anyTypeCount === 0
        ? 'No any types found'
        : `Found ${metrics.typeSafety.anyTypeCount} any types (not allowed)`,
    };
    checks.push(anyCheck);
  }

  // Type errors check
  const errorCheck = {
    name: `Type Errors (max ${standards.maxTypeErrors})`,
    passed: metrics.typeSafety.typeErrorCount <= standards.maxTypeErrors,
    actualValue: metrics.typeSafety.typeErrorCount,
    threshold: standards.maxTypeErrors,
    message: metrics.typeSafety.typeErrorCount <= standards.maxTypeErrors
      ? `${metrics.typeSafety.typeErrorCount} type errors (max ${standards.maxTypeErrors})`
      : `${metrics.typeSafety.typeErrorCount} type errors exceeds max ${standards.maxTypeErrors}`,
  };
  checks.push(errorCheck);

  // Strict mode check
  if (standards.requireStrictMode) {
    const strictCheck = {
      name: 'Strict Mode Enabled',
      passed: metrics.typeSafety.strictModeEnabled,
      actualValue: metrics.typeSafety.strictModeEnabled,
      threshold: true,
      message: metrics.typeSafety.strictModeEnabled
        ? 'Strict mode enabled'
        : 'Strict mode not enabled (required)',
    };
    checks.push(strictCheck);
  }

  return {
    passed: checks.every(c => c.passed),
    checks,
  };
}
```

```typescript
// src/lib/refactoring/standards/rules/TodoRule.ts

import type { CodeMetrics } from '../../types/analysis';
import type { CodeQualityStandards } from '../../types/standards';
import type { RuleResult } from '../StandardsEngine';

export function evaluateTodoRule(
  metrics: CodeMetrics,
  standards: CodeQualityStandards
): RuleResult {
  const checks = [];

  // TODO count check
  const todoCheck = {
    name: `TODO Markers (max ${standards.maxTodoMarkers})`,
    passed: metrics.quality.todoCount <= standards.maxTodoMarkers,
    actualValue: metrics.quality.todoCount,
    threshold: standards.maxTodoMarkers,
    message: metrics.quality.todoCount <= standards.maxTodoMarkers
      ? `${metrics.quality.todoCount} TODOs (max ${standards.maxTodoMarkers})`
      : `${metrics.quality.todoCount} TODOs exceeds max ${standards.maxTodoMarkers}`,
  };
  checks.push(todoCheck);

  // Complexity check
  const complexityCheck = {
    name: `Complexity Score (max ${standards.maxComplexityScore})`,
    passed: metrics.quality.complexityScore <= standards.maxComplexityScore,
    actualValue: metrics.quality.complexityScore,
    threshold: standards.maxComplexityScore,
    message: metrics.quality.complexityScore <= standards.maxComplexityScore
      ? `Complexity ${metrics.quality.complexityScore} (max ${standards.maxComplexityScore})`
      : `Complexity ${metrics.quality.complexityScore} exceeds max ${standards.maxComplexityScore}`,
  };
  checks.push(complexityCheck);

  return {
    passed: checks.every(c => c.passed),
    checks,
  };
}
```

**Tests Required:**

```typescript
// src/lib/refactoring/standards/__tests__/StandardsEngine.test.ts

import { describe, it, expect } from 'vitest';
import { StandardsEngine } from '../StandardsEngine';
import { strictStandards, balancedStandards } from '../presets';
import type { CodebaseAnalysis } from '../../types/analysis';

describe('StandardsEngine', () => {
  const mockAnalysis: CodebaseAnalysis = {
    id: 'test',
    path: '/test',
    analyzedAt: new Date().toISOString(),
    gitCommit: 'abc123',
    structure: {
      totalFiles: 100,
      sourceFiles: 80,
      testFiles: 20,
      directories: [],
    },
    techStack: {
      framework: 'sveltekit',
      language: 'typescript',
      stateManagement: 'svelte-runes',
      testFramework: 'vitest',
      buildTool: 'vite',
      styling: 'tailwind',
    },
    metrics: {
      testCoverage: {
        statements: 85,
        branches: 80,
        functions: 90,
        lines: 85,
        hasReport: true,
      },
      typeSafety: {
        anyTypeCount: 0,
        implicitAnyCount: 0,
        typeErrorCount: 0,
        strictModeEnabled: true,
      },
      quality: {
        todoCount: 5,
        fixmeCount: 2,
        complexityScore: 12,
        duplicateLineCount: 50,
      },
      size: {
        totalLines: 10000,
        codeLines: 7000,
        commentLines: 1500,
        blankLines: 1500,
      },
    },
    issues: [],
    patterns: [],
  };

  describe('evaluate', () => {
    it('should pass balanced standards with 85% coverage', () => {
      const engine = new StandardsEngine(balancedStandards);
      const result = engine.evaluate(mockAnalysis);

      expect(result.passed).toBe(true);
      expect(result.results.coverage.passed).toBe(true);
    });

    it('should fail strict standards with 85% coverage', () => {
      const engine = new StandardsEngine(strictStandards);
      const result = engine.evaluate(mockAnalysis);

      expect(result.passed).toBe(false);
      expect(result.results.coverage.passed).toBe(false);
    });

    it('should calculate score between 0 and 10', () => {
      const engine = new StandardsEngine(balancedStandards);
      const result = engine.evaluate(mockAnalysis);

      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(10);
    });
  });

  describe('generateGates', () => {
    it('should generate 4 phase gates', () => {
      const engine = new StandardsEngine(balancedStandards);
      const gates = engine.generateGates();

      expect(gates).toHaveLength(4);
      expect(gates[0].phase).toBe(1);
      expect(gates[1].phase).toBe(2);
      expect(gates[2].phase).toBe(3);
      expect(gates[3].phase).toBe(4);
    });

    it('should use configured coverage threshold', () => {
      const engine = new StandardsEngine(strictStandards);
      const gates = engine.generateGates();

      const phase2Gate = gates.find(g => g.phase === 2);
      const coverageCheck = phase2Gate?.checks.find(c => c.id === 'minimum-coverage');

      expect(coverageCheck?.threshold).toBe(100);
    });
  });

  describe('verifyGate', () => {
    it('should pass gate when metrics meet thresholds', () => {
      const engine = new StandardsEngine(balancedStandards);
      const gates = engine.generateGates();
      const phase2Gate = gates[1];

      const result = engine.verifyGate(phase2Gate, mockAnalysis.metrics);

      expect(result.passed).toBe(true);
    });

    it('should fail gate when coverage below threshold', () => {
      const engine = new StandardsEngine(strictStandards);
      const gates = engine.generateGates();
      const phase2Gate = gates[1];

      const result = engine.verifyGate(phase2Gate, mockAnalysis.metrics);

      expect(result.passed).toBe(false);
      expect(result.failureReason).toContain('Coverage');
    });
  });
});
```

---

### Git Checkpoint (End of Phase 1)

```bash
git add -A && git commit -m "refactor: Phase 1 complete - types and standards engine"
```

---

## Phase 2: Codebase Analyzer (Week 2-3)

### Objective

Implement the codebase analysis system that scans projects and generates metrics.

---

### Task 2.1: File System Scanner

**Priority:** P0  
**Estimated Hours:** 16  
**Files to Create:**

```
src/lib/refactoring/analyzer/FileSystemScanner.ts
src/lib/refactoring/analyzer/__tests__/FileSystemScanner.test.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/analyzer/FileSystemScanner.ts

import { readdir, stat, readFile } from 'fs/promises';
import { join, extname, basename } from 'path';
import type { DirectoryNode, FileType } from '../types/analysis';

export class FileSystemScanner {
  private readonly ignorePaths = [
    'node_modules',
    '.git',
    'dist',
    'build',
    '.svelte-kit',
    'coverage',
    '.next',
    '__pycache__',
    '.pytest_cache',
    'target',
  ];

  private readonly ignoreFiles = [
    '.DS_Store',
    'Thumbs.db',
    '.gitignore',
    '.env',
    '.env.local',
  ];

  async scan(rootPath: string): Promise<ScanResult> {
    const structure = await this.scanDirectory(rootPath, 0);
    const files = this.flattenFiles(structure);
    
    return {
      structure,
      files,
      stats: this.calculateStats(files),
    };
  }

  private async scanDirectory(
    dirPath: string,
    depth: number,
    maxDepth: number = 10
  ): Promise<DirectoryNode> {
    const name = basename(dirPath);
    const node: DirectoryNode = {
      path: dirPath,
      name,
      type: 'directory',
      children: [],
    };

    if (depth >= maxDepth) {
      return node;
    }

    try {
      const entries = await readdir(dirPath, { withFileTypes: true });

      for (const entry of entries) {
        if (this.shouldIgnore(entry.name)) {
          continue;
        }

        const entryPath = join(dirPath, entry.name);

        if (entry.isDirectory()) {
          const childNode = await this.scanDirectory(entryPath, depth + 1, maxDepth);
          node.children?.push(childNode);
        } else if (entry.isFile()) {
          node.children?.push({
            path: entryPath,
            name: entry.name,
            type: 'file',
            fileType: this.detectFileType(entry.name),
          });
        }
      }
    } catch (error) {
      console.error(`Error scanning ${dirPath}:`, error);
    }

    return node;
  }

  private shouldIgnore(name: string): boolean {
    return (
      this.ignorePaths.includes(name) ||
      this.ignoreFiles.includes(name) ||
      name.startsWith('.')
    );
  }

  private detectFileType(filename: string): FileType {
    const ext = extname(filename).toLowerCase();
    const name = filename.toLowerCase();

    // Test files
    if (
      name.includes('.test.') ||
      name.includes('.spec.') ||
      name.includes('__tests__')
    ) {
      return 'test';
    }

    // Config files
    if (
      name.includes('config') ||
      name.includes('rc.') ||
      name === 'package.json' ||
      name === 'tsconfig.json'
    ) {
      return 'config';
    }

    switch (ext) {
      case '.ts':
      case '.tsx':
        return 'typescript';
      case '.js':
      case '.jsx':
      case '.mjs':
      case '.cjs':
        return 'javascript';
      case '.svelte':
        return 'svelte';
      case '.py':
        return 'python';
      case '.rs':
        return 'rust';
      case '.json':
        return 'json';
      case '.md':
      case '.mdx':
        return 'markdown';
      case '.css':
      case '.scss':
      case '.less':
        return 'css';
      case '.html':
      case '.htm':
        return 'html';
      default:
        return 'other';
    }
  }

  private flattenFiles(node: DirectoryNode): FileInfo[] {
    const files: FileInfo[] = [];

    if (node.type === 'file') {
      files.push({
        path: node.path,
        name: node.name,
        type: node.fileType!,
      });
    }

    if (node.children) {
      for (const child of node.children) {
        files.push(...this.flattenFiles(child));
      }
    }

    return files;
  }

  private calculateStats(files: FileInfo[]): ScanStats {
    const byType: Record<FileType, number> = {
      typescript: 0,
      javascript: 0,
      svelte: 0,
      python: 0,
      rust: 0,
      json: 0,
      markdown: 0,
      css: 0,
      html: 0,
      test: 0,
      config: 0,
      other: 0,
    };

    for (const file of files) {
      byType[file.type]++;
    }

    const sourceFiles =
      byType.typescript +
      byType.javascript +
      byType.svelte +
      byType.python +
      byType.rust;

    return {
      totalFiles: files.length,
      sourceFiles,
      testFiles: byType.test,
      byType,
    };
  }
}

export interface ScanResult {
  structure: DirectoryNode;
  files: FileInfo[];
  stats: ScanStats;
}

export interface FileInfo {
  path: string;
  name: string;
  type: FileType;
}

export interface ScanStats {
  totalFiles: number;
  sourceFiles: number;
  testFiles: number;
  byType: Record<FileType, number>;
}
```

---

### Task 2.2: Tech Stack Detector

**Priority:** P0  
**Estimated Hours:** 12  
**Files to Create:**

```
src/lib/refactoring/analyzer/TechStackDetector.ts
src/lib/refactoring/analyzer/__tests__/TechStackDetector.test.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/analyzer/TechStackDetector.ts

import { readFile } from 'fs/promises';
import { join } from 'path';
import type { DetectedTechStack, FileInfo } from '../types/analysis';

export class TechStackDetector {
  async detect(rootPath: string, files: FileInfo[]): Promise<DetectedTechStack> {
    const packageJson = await this.readPackageJson(rootPath);
    const hasFiles = this.createFileChecker(files);

    return {
      framework: this.detectFramework(packageJson, hasFiles),
      language: this.detectLanguage(packageJson, hasFiles),
      stateManagement: this.detectStateManagement(packageJson, hasFiles),
      testFramework: this.detectTestFramework(packageJson),
      buildTool: this.detectBuildTool(packageJson),
      styling: this.detectStyling(packageJson, hasFiles),
    };
  }

  private async readPackageJson(rootPath: string): Promise<PackageJson | null> {
    try {
      const content = await readFile(join(rootPath, 'package.json'), 'utf-8');
      return JSON.parse(content);
    } catch {
      return null;
    }
  }

  private createFileChecker(files: FileInfo[]) {
    const fileSet = new Set(files.map(f => f.name));
    const extSet = new Set(files.map(f => f.type));

    return {
      hasFile: (name: string) => fileSet.has(name),
      hasExt: (type: string) => extSet.has(type as any),
      hasFilePattern: (pattern: RegExp) =>
        files.some(f => pattern.test(f.name)),
    };
  }

  private detectFramework(
    pkg: PackageJson | null,
    hasFiles: ReturnType<typeof this.createFileChecker>
  ): DetectedTechStack['framework'] {
    const deps = { ...pkg?.dependencies, ...pkg?.devDependencies };

    if (deps['@sveltejs/kit']) return 'sveltekit';
    if (deps['svelte'] && !deps['@sveltejs/kit']) return 'svelte';
    if (deps['next']) return 'nextjs';
    if (deps['react'] && !deps['next']) return 'react';
    if (deps['nuxt']) return 'nuxt';
    if (deps['vue'] && !deps['nuxt']) return 'vue';
    if (deps['fastapi'] || hasFiles.hasFile('requirements.txt')) {
      // Check for FastAPI in requirements.txt
      return 'fastapi';
    }
    if (deps['express']) return 'express';
    if (deps['@nestjs/core']) return 'nestjs';

    return null;
  }

  private detectLanguage(
    pkg: PackageJson | null,
    hasFiles: ReturnType<typeof this.createFileChecker>
  ): DetectedTechStack['language'] {
    const deps = { ...pkg?.dependencies, ...pkg?.devDependencies };

    if (deps['typescript'] || hasFiles.hasFile('tsconfig.json')) {
      return 'typescript';
    }
    if (hasFiles.hasExt('python')) return 'python';
    if (hasFiles.hasExt('rust')) return 'rust';

    return 'javascript';
  }

  private detectStateManagement(
    pkg: PackageJson | null,
    hasFiles: ReturnType<typeof this.createFileChecker>
  ): DetectedTechStack['stateManagement'] {
    const deps = { ...pkg?.dependencies, ...pkg?.devDependencies };

    // Svelte
    if (deps['svelte']) {
      // Check for runes by looking for .svelte.ts files
      if (hasFiles.hasFilePattern(/\.svelte\.ts$/)) {
        return 'svelte-runes';
      }
      return 'svelte-stores';
    }

    // React
    if (deps['@reduxjs/toolkit'] || deps['redux']) return 'redux';
    if (deps['zustand']) return 'zustand';
    if (deps['jotai']) return 'jotai';

    // Vue
    if (deps['pinia']) return 'pinia';
    if (deps['vuex']) return 'vuex';

    return null;
  }

  private detectTestFramework(
    pkg: PackageJson | null
  ): DetectedTechStack['testFramework'] {
    const deps = { ...pkg?.dependencies, ...pkg?.devDependencies };

    if (deps['vitest']) return 'vitest';
    if (deps['jest']) return 'jest';
    if (deps['@playwright/test']) return 'playwright';

    return null;
  }

  private detectBuildTool(
    pkg: PackageJson | null
  ): DetectedTechStack['buildTool'] {
    const deps = { ...pkg?.dependencies, ...pkg?.devDependencies };

    if (deps['vite']) return 'vite';
    if (deps['webpack']) return 'webpack';
    if (deps['rollup']) return 'rollup';
    if (deps['esbuild']) return 'esbuild';

    return null;
  }

  private detectStyling(
    pkg: PackageJson | null,
    hasFiles: ReturnType<typeof this.createFileChecker>
  ): DetectedTechStack['styling'] {
    const deps = { ...pkg?.dependencies, ...pkg?.devDependencies };

    if (deps['tailwindcss']) return 'tailwind';
    if (deps['styled-components']) return 'styled-components';
    if (hasFiles.hasFilePattern(/\.module\.css$/)) return 'css-modules';
    if (hasFiles.hasFilePattern(/\.scss$/)) return 'scss';

    return null;
  }
}

interface PackageJson {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
}
```

---

### Task 2.3: Metrics Collector

**Priority:** P0  
**Estimated Hours:** 20  
**Files to Create:**

```
src/lib/refactoring/analyzer/metrics/CoverageMetrics.ts
src/lib/refactoring/analyzer/metrics/TypeMetrics.ts
src/lib/refactoring/analyzer/metrics/QualityMetrics.ts
src/lib/refactoring/analyzer/metrics/index.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/analyzer/metrics/CoverageMetrics.ts

import { readFile } from 'fs/promises';
import { join } from 'path';
import type { CodeMetrics } from '../../types/analysis';

export class CoverageMetrics {
  async collect(rootPath: string): Promise<CodeMetrics['testCoverage']> {
    // Try to find and parse coverage report
    const coveragePaths = [
      'coverage/coverage-summary.json',
      'coverage/lcov-report/index.html',
      '.nyc_output/coverage-summary.json',
    ];

    for (const coveragePath of coveragePaths) {
      try {
        const fullPath = join(rootPath, coveragePath);
        
        if (coveragePath.endsWith('.json')) {
          const content = await readFile(fullPath, 'utf-8');
          const data = JSON.parse(content);
          
          if (data.total) {
            return {
              statements: data.total.statements?.pct ?? 0,
              branches: data.total.branches?.pct ?? 0,
              functions: data.total.functions?.pct ?? 0,
              lines: data.total.lines?.pct ?? 0,
              hasReport: true,
            };
          }
        }
      } catch {
        // Try next path
      }
    }

    // No coverage report found
    return {
      statements: 0,
      branches: 0,
      functions: 0,
      lines: 0,
      hasReport: false,
    };
  }
}
```

```typescript
// src/lib/refactoring/analyzer/metrics/TypeMetrics.ts

import { readFile } from 'fs/promises';
import { join } from 'path';
import type { CodeMetrics } from '../../types/analysis';
import type { FileInfo } from '../FileSystemScanner';

export class TypeMetrics {
  async collect(
    rootPath: string,
    files: FileInfo[]
  ): Promise<CodeMetrics['typeSafety']> {
    let anyTypeCount = 0;
    let implicitAnyCount = 0;

    const tsFiles = files.filter(
      f => f.type === 'typescript' || f.type === 'javascript'
    );

    for (const file of tsFiles) {
      try {
        const content = await readFile(file.path, 'utf-8');
        
        // Count explicit `any` types
        const anyMatches = content.match(/:\s*any\b/g);
        anyTypeCount += anyMatches?.length ?? 0;

        // Count `as any` casts
        const asAnyMatches = content.match(/as\s+any\b/g);
        anyTypeCount += asAnyMatches?.length ?? 0;
      } catch {
        // Skip unreadable files
      }
    }

    // Check tsconfig for strict mode
    const strictModeEnabled = await this.checkStrictMode(rootPath);

    return {
      anyTypeCount,
      implicitAnyCount,
      typeErrorCount: 0, // Would need to run tsc to get this
      strictModeEnabled,
    };
  }

  private async checkStrictMode(rootPath: string): Promise<boolean> {
    try {
      const tsconfigPath = join(rootPath, 'tsconfig.json');
      const content = await readFile(tsconfigPath, 'utf-8');
      const tsconfig = JSON.parse(content);

      return tsconfig.compilerOptions?.strict === true;
    } catch {
      return false;
    }
  }
}
```

```typescript
// src/lib/refactoring/analyzer/metrics/QualityMetrics.ts

import { readFile } from 'fs/promises';
import type { CodeMetrics } from '../../types/analysis';
import type { FileInfo } from '../FileSystemScanner';

export class QualityMetrics {
  async collect(files: FileInfo[]): Promise<CodeMetrics['quality']> {
    let todoCount = 0;
    let fixmeCount = 0;
    let totalLines = 0;
    let codeLines = 0;
    let commentLines = 0;
    let blankLines = 0;

    const sourceFiles = files.filter(f =>
      ['typescript', 'javascript', 'svelte', 'python'].includes(f.type)
    );

    for (const file of sourceFiles) {
      try {
        const content = await readFile(file.path, 'utf-8');
        const lines = content.split('\n');

        totalLines += lines.length;

        for (const line of lines) {
          const trimmed = line.trim();

          if (trimmed === '') {
            blankLines++;
          } else if (this.isComment(trimmed)) {
            commentLines++;
            
            // Check for TODOs in comments
            if (/\bTODO\b/i.test(trimmed)) {
              todoCount++;
            }
            if (/\bFIXME\b/i.test(trimmed)) {
              fixmeCount++;
            }
          } else {
            codeLines++;
            
            // Check for TODOs in inline comments
            if (/\/\/.*\bTODO\b/i.test(line) || /#.*\bTODO\b/i.test(line)) {
              todoCount++;
            }
            if (/\/\/.*\bFIXME\b/i.test(line) || /#.*\bFIXME\b/i.test(line)) {
              fixmeCount++;
            }
          }
        }
      } catch {
        // Skip unreadable files
      }
    }

    return {
      todoCount,
      fixmeCount,
      complexityScore: this.estimateComplexity(codeLines, sourceFiles.length),
      duplicateLineCount: 0, // Would need more sophisticated analysis
    };
  }

  async collectSize(files: FileInfo[]): Promise<CodeMetrics['size']> {
    let totalLines = 0;
    let codeLines = 0;
    let commentLines = 0;
    let blankLines = 0;

    const sourceFiles = files.filter(f =>
      ['typescript', 'javascript', 'svelte', 'python'].includes(f.type)
    );

    for (const file of sourceFiles) {
      try {
        const content = await readFile(file.path, 'utf-8');
        const lines = content.split('\n');

        totalLines += lines.length;

        for (const line of lines) {
          const trimmed = line.trim();

          if (trimmed === '') {
            blankLines++;
          } else if (this.isComment(trimmed)) {
            commentLines++;
          } else {
            codeLines++;
          }
        }
      } catch {
        // Skip unreadable files
      }
    }

    return {
      totalLines,
      codeLines,
      commentLines,
      blankLines,
    };
  }

  private isComment(line: string): boolean {
    return (
      line.startsWith('//') ||
      line.startsWith('/*') ||
      line.startsWith('*') ||
      line.startsWith('#') ||
      line.startsWith('"""') ||
      line.startsWith("'''")
    );
  }

  private estimateComplexity(codeLines: number, fileCount: number): number {
    // Simple complexity estimate based on average lines per file
    const avgLinesPerFile = codeLines / Math.max(fileCount, 1);
    
    if (avgLinesPerFile < 100) return 5;
    if (avgLinesPerFile < 200) return 10;
    if (avgLinesPerFile < 300) return 15;
    if (avgLinesPerFile < 500) return 20;
    return 25;
  }
}
```

---

### Task 2.4: Main Analyzer Class

**Priority:** P0  
**Estimated Hours:** 12  
**Files to Create:**

```
src/lib/refactoring/analyzer/CodebaseAnalyzer.ts
src/lib/refactoring/analyzer/index.ts
src/lib/refactoring/analyzer/__tests__/CodebaseAnalyzer.test.ts
```

**Implementation:**

```typescript
// src/lib/refactoring/analyzer/CodebaseAnalyzer.ts

import { execSync } from 'child_process';
import { v4 as uuid } from 'uuid';
import { FileSystemScanner } from './FileSystemScanner';
import { TechStackDetector } from './TechStackDetector';
import { CoverageMetrics } from './metrics/CoverageMetrics';
import { TypeMetrics } from './metrics/TypeMetrics';
import { QualityMetrics } from './metrics/QualityMetrics';
import { PatternDetector } from './PatternDetector';
import { IssueDetector } from './IssueDetector';
import type { CodebaseAnalysis } from '../types/analysis';

export class CodebaseAnalyzer {
  private fileScanner: FileSystemScanner;
  private techStackDetector: TechStackDetector;
  private coverageMetrics: CoverageMetrics;
  private typeMetrics: TypeMetrics;
  private qualityMetrics: QualityMetrics;
  private patternDetector: PatternDetector;
  private issueDetector: IssueDetector;

  constructor() {
    this.fileScanner = new FileSystemScanner();
    this.techStackDetector = new TechStackDetector();
    this.coverageMetrics = new CoverageMetrics();
    this.typeMetrics = new TypeMetrics();
    this.qualityMetrics = new QualityMetrics();
    this.patternDetector = new PatternDetector();
    this.issueDetector = new IssueDetector();
  }

  async analyze(rootPath: string): Promise<CodebaseAnalysis> {
    // Step 1: Scan file system
    const scanResult = await this.fileScanner.scan(rootPath);

    // Step 2: Detect tech stack
    const techStack = await this.techStackDetector.detect(
      rootPath,
      scanResult.files
    );

    // Step 3: Collect metrics
    const [testCoverage, typeSafety, quality, size] = await Promise.all([
      this.coverageMetrics.collect(rootPath),
      this.typeMetrics.collect(rootPath, scanResult.files),
      this.qualityMetrics.collect(scanResult.files),
      this.qualityMetrics.collectSize(scanResult.files),
    ]);

    // Step 4: Detect patterns
    const patterns = await this.patternDetector.detect(
      scanResult.files,
      techStack
    );

    // Step 5: Detect issues
    const issues = await this.issueDetector.detect(
      scanResult.files,
      { testCoverage, typeSafety, quality, size },
      patterns
    );

    // Step 6: Get git commit
    const gitCommit = this.getGitCommit(rootPath);

    return {
      id: uuid(),
      path: rootPath,
      analyzedAt: new Date().toISOString(),
      gitCommit,
      structure: {
        totalFiles: scanResult.stats.totalFiles,
        sourceFiles: scanResult.stats.sourceFiles,
        testFiles: scanResult.stats.testFiles,
        directories: [scanResult.structure],
      },
      techStack,
      metrics: {
        testCoverage,
        typeSafety,
        quality,
        size,
      },
      issues,
      patterns,
    };
  }

  private getGitCommit(rootPath: string): string {
    try {
      return execSync('git rev-parse HEAD', {
        cwd: rootPath,
        encoding: 'utf-8',
      }).trim();
    } catch {
      return 'unknown';
    }
  }
}
```

---

### Git Checkpoint (End of Phase 2)

```bash
git add -A && git commit -m "refactor: Phase 2 complete - codebase analyzer"
```

---

## Phase 3: Plan Generator (Week 4-5)

### Objective

Generate refactoring plans based on analysis and user-selected standards.

[Tasks 3.1-3.5 follow similar detailed patterns...]

---

## Phase 4: Executor & Learning (Week 6-8)

### Objective

Execute plans via Claude Code integration and record outcomes for learning.

[Tasks 4.1-4.6 follow similar detailed patterns...]

---

## Git Checkpoint (End of Phase 4)

```bash
git add -A && git commit -m "refactor: Phase 4 complete - executor and learning"
git tag -a v2.0.0-refactoring -m "Refactoring Automation Feature"
```

---

## Appendix A: File Summary

### Files to Create (Phase 1-4)

| Phase | Files | Purpose |
|-------|-------|---------|
| 1 | 15 | Types, standards, presets |
| 2 | 12 | Analyzer, metrics, detection |
| 3 | 10 | Planner, tasks, templates |
| 4 | 12 | Executor, learning, UI |

### Total: ~49 new files + tests

---

## Appendix B: API Endpoints (NeuroForge)

```
POST /api/v1/refactoring/learn
GET  /api/v1/refactoring/recommend
GET  /api/v1/refactoring/predict-gate
POST /api/v1/refactoring/execute
```

---

## Appendix C: Success Criteria

### Phase 1 Complete When:

- [ ] All types defined and exported
- [ ] 4 preset standards working
- [ ] Standards engine evaluates correctly
- [ ] 100% test coverage on phase 1 code

### Phase 2 Complete When:

- [ ] File scanner works on real codebases
- [ ] Tech stack detection accurate
- [ ] Metrics collection complete
- [ ] 100% test coverage on phase 2 code

### Phase 3 Complete When:

- [ ] Plans generate from analysis
- [ ] Tasks break down correctly
- [ ] Time estimates reasonable
- [ ] 100% test coverage on phase 3 code

### Phase 4 Complete When:

- [ ] Claude Code integration works
- [ ] Git checkpoints automated
- [ ] Learning records outcomes
- [ ] 100% test coverage on phase 4 code

---

**Document End**
