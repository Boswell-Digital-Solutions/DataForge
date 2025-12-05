# VibeForge Refactoring Automation - Claude Code Prompt

**Feature:** Automated Refactoring with Learning  
**Estimated Effort:** 320 hours (8 weeks)  
**Prerequisites:** VibeForge 1.0 core complete

---

## ⚠️ MANDATORY: 100% TEST COVERAGE

This is a Forge product. Every function, component, and API call ships with tests. No exceptions. If coverage is not 100%, do not proceed to next phase.

---

## Project Context

You are implementing automated refactoring capabilities for VibeForge - a prompt engineering workbench. This feature allows users to:

1. **Analyze** codebases (scan files, detect tech stack, collect metrics)
2. **Configure** quality standards (user chooses their rules, not ours)
3. **Generate** refactoring plans (tasks, phases, gates)
4. **Execute** plans via Claude Code integration
5. **Learn** from outcomes via NeuroForge

### Key Principle

**User-defined standards.** The 100% coverage rule is OUR internal standard. Users choose their own thresholds (40%, 60%, 80%, 100%). The system enforces whatever THEY configure.

---

## Architecture Rules

```
NEVER create +server.ts files (Tauri desktop app, no server routes)
ALWAYS use Svelte 5 runes ($state, $derived, $effect)
ALWAYS prefix env vars with VITE_
ALWAYS use neuroforgeClient/dataforgeClient for API calls
ALWAYS co-locate tests with source files
```

---

## Directory Structure

```
src/lib/refactoring/
├── analyzer/
│   ├── CodebaseAnalyzer.ts
│   ├── FileSystemScanner.ts
│   ├── TechStackDetector.ts
│   ├── PatternDetector.ts
│   ├── IssueDetector.ts
│   ├── metrics/
│   │   ├── CoverageMetrics.ts
│   │   ├── TypeMetrics.ts
│   │   └── QualityMetrics.ts
│   └── __tests__/
├── standards/
│   ├── StandardsEngine.ts
│   ├── presets/
│   │   ├── strict.ts       (100% coverage)
│   │   ├── balanced.ts     (80% coverage)
│   │   ├── startup.ts      (60% coverage)
│   │   └── legacy.ts       (40% coverage)
│   ├── rules/
│   └── __tests__/
├── planner/
│   ├── RefactoringPlanner.ts
│   ├── TaskGenerator.ts
│   ├── PhaseGenerator.ts
│   ├── EstimationEngine.ts
│   └── __tests__/
├── executor/
│   ├── RefactoringExecutor.ts
│   ├── ClaudeCodeBridge.ts
│   ├── GitOperations.ts
│   ├── GateVerifier.ts
│   └── __tests__/
├── learning/
│   ├── LearningClient.ts
│   ├── OutcomeRecorder.ts
│   ├── RecommendationEngine.ts
│   └── __tests__/
├── types/
│   ├── analysis.ts
│   ├── standards.ts
│   ├── planning.ts
│   ├── execution.ts
│   └── learning.ts
└── stores/
    ├── refactoringProject.svelte.ts
    ├── analysisResults.svelte.ts
    └── executionProgress.svelte.ts
```

---

## Code Patterns

### Type Definition Pattern

```typescript
// src/lib/refactoring/types/standards.ts
export interface QualityStandards {
  id: string;
  name: string;
  testing: {
    minimumCoverage: number;  // User's choice: 40, 60, 80, or 100
    requireUnitTests: boolean;
    requireComponentTests: boolean;
  };
  typeSafety: {
    allowAnyTypes: boolean;   // User's choice
    maxTypeErrors: number;
  };
  // ... more fields
}
```

### Preset Pattern

```typescript
// src/lib/refactoring/standards/presets/balanced.ts
import type { QualityStandards } from '../../types/standards';

export const balancedStandards: QualityStandards = {
  id: 'preset-balanced',
  name: 'Balanced',
  description: '80% coverage, pragmatic quality.',
  isDefault: true,
  testing: {
    minimumCoverage: 80,
    requireUnitTests: true,
    requireComponentTests: true,
  },
  // ...
};
```

### Standards Engine Pattern

```typescript
// src/lib/refactoring/standards/StandardsEngine.ts
export class StandardsEngine {
  private standards: QualityStandards;

  constructor(standards: QualityStandards) {
    this.standards = standards;
  }

  evaluate(analysis: CodebaseAnalysis): StandardsEvaluation {
    // Evaluate against USER's configured standards
    const coveragePassed = 
      analysis.metrics.testCoverage.lines >= this.standards.testing.minimumCoverage;
    // ...
  }

  generateGates(): QualityGate[] {
    // Generate gates based on USER's thresholds
    return [{
      name: 'Phase 2: Test Coverage',
      checks: [{
        id: 'minimum-coverage',
        name: `Coverage ≥ ${this.standards.testing.minimumCoverage}%`,
        threshold: this.standards.testing.minimumCoverage,
      }],
    }];
  }
}
```

### Analyzer Pattern

```typescript
// src/lib/refactoring/analyzer/CodebaseAnalyzer.ts
export class CodebaseAnalyzer {
  async analyze(rootPath: string): Promise<CodebaseAnalysis> {
    const scanResult = await this.fileScanner.scan(rootPath);
    const techStack = await this.techStackDetector.detect(rootPath, scanResult.files);
    const metrics = await this.collectMetrics(rootPath, scanResult.files);
    const patterns = await this.patternDetector.detect(scanResult.files, techStack);
    const issues = await this.issueDetector.detect(scanResult.files, metrics, patterns);

    return {
      id: uuid(),
      path: rootPath,
      analyzedAt: new Date().toISOString(),
      gitCommit: this.getGitCommit(rootPath),
      structure: { /* ... */ },
      techStack,
      metrics,
      issues,
      patterns,
    };
  }
}
```

### Svelte 5 Store Pattern

```typescript
// src/lib/refactoring/stores/refactoringProject.svelte.ts
import type { RefactoringProject } from '../types/execution';

class RefactoringProjectStore {
  project = $state<RefactoringProject | null>(null);
  isLoading = $state(false);
  error = $state<string | null>(null);

  hasProject = $derived(this.project !== null);
  progress = $derived(this.project?.progress.percentage ?? 0);

  async loadProject(id: string): Promise<void> {
    this.isLoading = true;
    this.error = null;
    try {
      this.project = await dataforgeClient.getRefactoringProject(id);
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      this.isLoading = false;
    }
  }

  reset(): void {
    this.project = null;
    this.error = null;
  }
}

export const refactoringProjectStore = new RefactoringProjectStore();
```

### Test Pattern

```typescript
// src/lib/refactoring/standards/__tests__/StandardsEngine.test.ts
import { describe, it, expect } from 'vitest';
import { StandardsEngine } from '../StandardsEngine';
import { balancedStandards, strictStandards } from '../presets';

describe('StandardsEngine', () => {
  describe('evaluate', () => {
    it('should pass when coverage meets user threshold', () => {
      const engine = new StandardsEngine(balancedStandards); // 80%
      const analysis = createMockAnalysis({ coverage: 85 });
      
      const result = engine.evaluate(analysis);
      
      expect(result.passed).toBe(true);
    });

    it('should fail when coverage below user threshold', () => {
      const engine = new StandardsEngine(strictStandards); // 100%
      const analysis = createMockAnalysis({ coverage: 85 });
      
      const result = engine.evaluate(analysis);
      
      expect(result.passed).toBe(false);
    });

    it('should respect user allowAnyTypes setting', () => {
      const permissiveStandards = { ...balancedStandards, typeSafety: { allowAnyTypes: true } };
      const engine = new StandardsEngine(permissiveStandards);
      const analysis = createMockAnalysis({ anyTypes: 10 });
      
      const result = engine.evaluate(analysis);
      
      expect(result.results.typeSafety.passed).toBe(true);
    });
  });

  describe('generateGates', () => {
    it('should use configured coverage threshold', () => {
      const engine = new StandardsEngine(strictStandards);
      const gates = engine.generateGates();
      
      const coverageCheck = gates[1].checks.find(c => c.id === 'minimum-coverage');
      expect(coverageCheck?.threshold).toBe(100);
    });
  });
});
```

---

## Task Sequence

### Phase 1: Types & Standards (Week 1)

| Task | Description | Hours |
|------|-------------|-------|
| 1.1 | Create type definitions (analysis, standards, planning, execution, learning) | 8 |
| 1.2 | Create 4 preset standards (strict/balanced/startup/legacy) | 8 |
| 1.3 | Implement StandardsEngine (evaluate, generateGates, verifyGate) | 16 |
| 1.4 | Implement rule evaluators (coverage, type safety, todos) | 8 |
| 1.5 | Write tests for all Phase 1 code (100% coverage) | 8 |

**Gate:** `pnpm test:coverage` shows 100% for Phase 1 files

```bash
git add -A && git commit -m "refactor: Phase 1 complete - types and standards"
```

### Phase 2: Analyzer (Week 2-3)

| Task | Description | Hours |
|------|-------------|-------|
| 2.1 | Implement FileSystemScanner (scan directories, detect file types) | 16 |
| 2.2 | Implement TechStackDetector (framework, language, state management) | 12 |
| 2.3 | Implement metrics collectors (coverage, types, quality, size) | 20 |
| 2.4 | Implement PatternDetector (store patterns, API patterns) | 12 |
| 2.5 | Implement IssueDetector (find problems from metrics) | 8 |
| 2.6 | Implement CodebaseAnalyzer (orchestrate all above) | 8 |
| 2.7 | Write tests for all Phase 2 code (100% coverage) | 16 |

**Gate:** `pnpm test:coverage` shows 100% for Phase 2 files

```bash
git add -A && git commit -m "refactor: Phase 2 complete - codebase analyzer"
```

### Phase 3: Planner (Week 4-5)

| Task | Description | Hours |
|------|-------------|-------|
| 3.1 | Implement TaskGenerator (break analysis into tasks) | 16 |
| 3.2 | Implement PhaseGenerator (group tasks into phases) | 12 |
| 3.3 | Implement EstimationEngine (time estimates with learning input) | 12 |
| 3.4 | Implement RefactoringPlanner (orchestrate plan generation) | 12 |
| 3.5 | Create plan templates (test-coverage, type-safety, store-migration) | 8 |
| 3.6 | Implement document generators (implementation plan, Claude prompt) | 8 |
| 3.7 | Write tests for all Phase 3 code (100% coverage) | 16 |

**Gate:** `pnpm test:coverage` shows 100% for Phase 3 files

```bash
git add -A && git commit -m "refactor: Phase 3 complete - plan generator"
```

### Phase 4: Executor & Learning (Week 6-8)

| Task | Description | Hours |
|------|-------------|-------|
| 4.1 | Implement GitOperations (branch, commit, checkpoint, rollback) | 12 |
| 4.2 | Implement GateVerifier (run commands, check thresholds) | 12 |
| 4.3 | Implement ClaudeCodeBridge (spawn Claude Code, stream output) | 20 |
| 4.4 | Implement RefactoringExecutor (orchestrate execution) | 16 |
| 4.5 | Implement LearningClient (record outcomes to NeuroForge) | 12 |
| 4.6 | Implement RecommendationEngine (get learned recommendations) | 12 |
| 4.7 | Create Svelte stores (project, analysis, progress) | 8 |
| 4.8 | Write tests for all Phase 4 code (100% coverage) | 24 |

**Gate:** `pnpm test:coverage` shows 100% for Phase 4 files

```bash
git add -A && git commit -m "refactor: Phase 4 complete - executor and learning"
git tag -a v2.0.0-refactoring -m "Refactoring Automation Feature"
```

---

## Test Coverage Requirements

### What Must Be Tested

```
✓ Every exported function
✓ Every class method
✓ Every store action
✓ All success paths
✓ All error paths
✓ All edge cases
✓ All type guards
```

### Coverage Commands

```bash
# Run tests with coverage
pnpm test:coverage

# Check specific file coverage
pnpm vitest run src/lib/refactoring/standards --coverage

# Watch mode during development
pnpm test:watch
```

### Coverage Thresholds (vitest.config.ts)

```typescript
coverage: {
  provider: 'v8',
  reporter: ['text', 'json', 'html'],
  exclude: ['**/*.test.ts', '**/__tests__/**'],
  thresholds: {
    statements: 100,
    branches: 100,
    functions: 100,
    lines: 100,
  },
}
```

---

## Verification Commands

```bash
# After each task
pnpm check          # TypeScript compilation
pnpm test           # All tests pass
pnpm test:coverage  # 100% coverage

# After each phase
pnpm build          # Production build
pnpm test:e2e       # E2E tests (if applicable)
```

---

## Key Files to Reference

```
src/lib/api/neuroforgeClient.ts    # API client pattern
src/lib/api/dataforgeClient.ts     # API client pattern
src/lib/stores/*.svelte.ts         # Store patterns
src/lib/types/*.ts                 # Type patterns
```

---

## Autonomous Execution Prompt

Copy this into Claude Code:

```
I'm implementing Refactoring Automation for VibeForge. Work through tasks sequentially:

PHASE 1: Types & Standards
- 1.1: Create src/lib/refactoring/types/ (analysis.ts, standards.ts, planning.ts, execution.ts, learning.ts)
- 1.2: Create src/lib/refactoring/standards/presets/ (strict.ts, balanced.ts, startup.ts, legacy.ts, index.ts)
- 1.3: Create src/lib/refactoring/standards/StandardsEngine.ts
- 1.4: Create src/lib/refactoring/standards/rules/ (CoverageRule.ts, TypeSafetyRule.ts, TodoRule.ts)
- 1.5: Create tests achieving 100% coverage for Phase 1

After Phase 1: git commit -m "refactor: Phase 1 complete - types and standards"

PHASE 2: Analyzer
- 2.1: Create src/lib/refactoring/analyzer/FileSystemScanner.ts
- 2.2: Create src/lib/refactoring/analyzer/TechStackDetector.ts
- 2.3: Create src/lib/refactoring/analyzer/metrics/ (CoverageMetrics.ts, TypeMetrics.ts, QualityMetrics.ts)
- 2.4: Create src/lib/refactoring/analyzer/PatternDetector.ts
- 2.5: Create src/lib/refactoring/analyzer/IssueDetector.ts
- 2.6: Create src/lib/refactoring/analyzer/CodebaseAnalyzer.ts
- 2.7: Create tests achieving 100% coverage for Phase 2

After Phase 2: git commit -m "refactor: Phase 2 complete - codebase analyzer"

PHASE 3: Planner
- 3.1-3.7: Implement planner components with 100% test coverage

After Phase 3: git commit -m "refactor: Phase 3 complete - plan generator"

PHASE 4: Executor & Learning
- 4.1-4.8: Implement executor and learning with 100% test coverage

After Phase 4: 
git commit -m "refactor: Phase 4 complete - executor and learning"
git tag -a v2.0.0-refactoring -m "Refactoring Automation Feature"

RULES:
- Run `pnpm check` and `pnpm test` after each task
- 100% test coverage is MANDATORY - do not proceed without it
- Use Svelte 5 runes for all stores
- Follow existing patterns in src/lib/api/ and src/lib/stores/
- KEY PRINCIPLE: Standards are USER-configurable, not hardcoded
```

---

## For Fully Autonomous Mode

```bash
claude --dangerously-skip-permissions
```

Then paste the autonomous prompt above.

**Safe because:**
- Specific file paths defined
- Only dev commands (pnpm check, test, build)
- Scoped to project directory
- Git provides rollback points

---

## Success Criteria

### Feature Complete When:

- [ ] User can select from 4 preset standards OR create custom
- [ ] Analyzer scans real codebases and produces accurate metrics
- [ ] Planner generates actionable refactoring plans
- [ ] Executor integrates with Claude Code for automated execution
- [ ] Learning records outcomes to NeuroForge
- [ ] Recommendations improve based on learned data
- [ ] 100% test coverage on ALL code
- [ ] All TypeScript strict checks pass
- [ ] Production build succeeds

---

**End of Prompt**
