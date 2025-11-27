# VibeForge Code Analysis & GitHub Integration

**Version:** 1.0  
**Created:** November 26, 2025  
**Total AI Execution Time:** 8-12 hours

---

## Overview

This plan implements two interconnected features:

1. **Analysis UI (Option C)** - Editor-centric with contextual analysis panel and inline Monaco markers
2. **GitHub Integration (Option C)** - Hybrid approach with API-fetched file tree and local caching

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Part 1: Analysis UI](#part-1-analysis-ui)
3. [Part 2: GitHub Integration](#part-2-github-integration)
4. [Part 3: Wiring It Together](#part-3-wiring-it-together)
5. [Database Schema](#database-schema)
6. [Implementation Phases](#implementation-phases)
7. [Claude Code Prompt](#claude-code-prompt)

---

## Architecture Overview

### Current State

```
src/lib/workbench/
├── context/          ✅ ContextColumn, blocks
├── prompt/           ✅ PromptColumn, MonacoEditor
├── output/           ✅ OutputColumn, results
└── components/       ✅ NewProjectWizard, QuickCreate

src/lib/refactoring/
├── analyzer/         ✅ CodebaseAnalyzer, IssueDetector, etc.
├── types/            ✅ Analysis types
└── standards/        ✅ StandardsEngine

src/lib/components/refactoring/
└── AnalysisResults.svelte  ✅ Results display (unused currently)
```

### Target State

```
src/lib/workbench/
├── context/          ✅ Existing
├── prompt/           ✅ Existing + inline markers
├── output/           ✅ Existing
├── components/       ✅ Existing
│
├── source/           🆕 NEW - GitHub & file management
│   ├── SourcePanel.svelte
│   ├── GitHubConnector.svelte
│   ├── FileTree.svelte
│   ├── FileTreeItem.svelte
│   └── index.ts
│
├── analysis/         🆕 NEW - Analysis panel & markers
│   ├── AnalysisPanel.svelte
│   ├── AnalysisDrawer.svelte
│   ├── IssueList.svelte
│   ├── IssueItem.svelte
│   ├── AnalysisSummary.svelte
│   ├── MonacoMarkers.ts
│   └── index.ts
│
└── stores/           🆕 NEW - Feature stores
    ├── source.svelte.ts
    ├── analysis.svelte.ts
    └── index.ts

src/lib/refactoring/
├── analyzer/         ✅ Existing + new adapter
│   └── EditorAnalyzer.ts   🆕 Analyze editor content (not files)
└── ...
```

---

## Part 1: Analysis UI

### User Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. User pastes/types code OR loads from GitHub                      │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. User clicks [Analyze] (or auto-analyze on paste)                 │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. EditorAnalyzer processes content                                 │
│    - Detects language/framework                                     │
│    - Finds issues (type safety, missing tests, etc.)                │
│    - Calculates metrics                                             │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. Results displayed:                                               │
│    - Inline squiggles in Monaco (red/yellow/blue)                   │
│    - Analysis drawer slides up from bottom                          │
│    - Summary metrics shown                                          │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. User can:                                                        │
│    - Click issue → jumps to line in editor                          │
│    - Click [Fix All] → generates fix prompts                        │
│    - Click [Generate Plan] → creates refactoring plan               │
│    - Click [Add Feature] → opens feature planner                    │
└─────────────────────────────────────────────────────────────────────┘
```

### UI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                    [Analyze ▼] [Run Prompt] │
├───────────────┬─────────────────────────────────────────────────────┤
│ LEFT COLUMN   │                                                     │
│               │  ┌─────────────────────────────────────────────┐   │
│ Context       │  │              Monaco Editor                  │   │
│ ─────────     │  │                                             │   │
│ + Add Block   │  │  1  export function processOrder(items) {  │   │
│               │  │  2    let total = 0;                        │   │
│ Source        │  │  3    for (var i in items) {  ~~~~~~~~~~~  │   │
│ ─────────     │  │  4      total += items[i].price;           │   │
│ 📁 Connected  │  │  5    }                       ^red squiggle│   │
│   └ src/      │  │  6    return total            ~~~~~~~~~~~  │   │
│   └ lib/      │  │  7  }                         ^yellow      │   │
│               │  │                                             │   │
│ [+ GitHub]    │  └─────────────────────────────────────────────┘   │
│ [+ Upload]    │                                                     │
│               │  ┌─────────────────────────────────────────────┐   │
│               │  │ ANALYSIS PANEL                        [—][×]│   │
│               │  ├─────────────────────────────────────────────┤   │
│               │  │ Summary: 2 errors, 1 warning, 3 suggestions │   │
│               │  ├─────────────────────────────────────────────┤   │
│               │  │ 🔴 Line 3: Use for...of instead of for...in │   │
│               │  │ 🔴 Line 6: Missing semicolon                │   │
│               │  │ 🟡 Line 1: Add TypeScript types             │   │
│               │  ├─────────────────────────────────────────────┤   │
│               │  │ [Fix All]  [Generate Plan]  [Add Feature]   │   │
│               │  └─────────────────────────────────────────────┘   │
└───────────────┴─────────────────────────────────────────────────────┘
```

### Components

#### 1. AnalysisDrawer.svelte

Collapsible bottom panel that contains analysis results.

```svelte
<script lang="ts">
  import { analysisStore } from '../stores/analysis.svelte';
  import AnalysisSummary from './AnalysisSummary.svelte';
  import IssueList from './IssueList.svelte';
  
  interface Props {
    onClose?: () => void;
    onGeneratePlan?: () => void;
    onAddFeature?: () => void;
  }
  
  let { onClose, onGeneratePlan, onAddFeature }: Props = $props();
  
  const analysis = $derived(analysisStore.current);
  const isOpen = $derived(analysisStore.drawerOpen);
  const isMinimized = $derived(analysisStore.drawerMinimized);
</script>

{#if isOpen && analysis}
  <div 
    class="analysis-drawer border-t border-slate-700 bg-forge-blacksteel transition-all duration-300"
    class:minimized={isMinimized}
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-slate-700">
      <div class="flex items-center gap-3">
        <span class="text-sm font-medium text-slate-200">Analysis Results</span>
        <AnalysisSummary summary={analysis.summary} compact />
      </div>
      <div class="flex items-center gap-1">
        <button onclick={() => analysisStore.toggleMinimize()} class="p-1 hover:bg-slate-700 rounded">
          {isMinimized ? '▲' : '▼'}
        </button>
        <button onclick={onClose} class="p-1 hover:bg-slate-700 rounded">✕</button>
      </div>
    </div>
    
    <!-- Content (hidden when minimized) -->
    {#if !isMinimized}
      <div class="flex-1 overflow-auto p-4 max-h-64">
        <IssueList issues={analysis.issues} />
      </div>
      
      <!-- Actions -->
      <div class="flex items-center gap-3 px-4 py-3 border-t border-slate-700">
        <button 
          class="px-4 py-2 bg-forge-ember text-white rounded-lg hover:bg-forge-ember/90"
          onclick={onGeneratePlan}
        >
          Generate Fix Plan
        </button>
        <button 
          class="px-4 py-2 bg-slate-700 text-slate-200 rounded-lg hover:bg-slate-600"
          onclick={onAddFeature}
        >
          Add Feature...
        </button>
      </div>
    {/if}
  </div>
{/if}
```

#### 2. IssueList.svelte

Displays issues grouped by severity.

```svelte
<script lang="ts">
  import type { CodeIssue } from '$lib/refactoring/types/analysis';
  import IssueItem from './IssueItem.svelte';
  
  interface Props {
    issues: CodeIssue[];
    onIssueClick?: (issue: CodeIssue) => void;
  }
  
  let { issues, onIssueClick }: Props = $props();
  
  const errors = $derived(issues.filter(i => i.severity === 'error'));
  const warnings = $derived(issues.filter(i => i.severity === 'warning'));
  const suggestions = $derived(issues.filter(i => i.severity === 'suggestion'));
</script>

<div class="space-y-4">
  {#if errors.length > 0}
    <div>
      <h4 class="text-sm font-medium text-red-400 mb-2">
        🔴 Errors ({errors.length})
      </h4>
      <div class="space-y-1">
        {#each errors as issue (issue.id)}
          <IssueItem {issue} onclick={() => onIssueClick?.(issue)} />
        {/each}
      </div>
    </div>
  {/if}
  
  {#if warnings.length > 0}
    <div>
      <h4 class="text-sm font-medium text-yellow-400 mb-2">
        🟡 Warnings ({warnings.length})
      </h4>
      <div class="space-y-1">
        {#each warnings as issue (issue.id)}
          <IssueItem {issue} onclick={() => onIssueClick?.(issue)} />
        {/each}
      </div>
    </div>
  {/if}
  
  {#if suggestions.length > 0}
    <div>
      <h4 class="text-sm font-medium text-blue-400 mb-2">
        🟢 Suggestions ({suggestions.length})
      </h4>
      <div class="space-y-1">
        {#each suggestions as issue (issue.id)}
          <IssueItem {issue} onclick={() => onIssueClick?.(issue)} />
        {/each}
      </div>
    </div>
  {/if}
</div>
```

#### 3. MonacoMarkers.ts

Utility to add inline markers to Monaco editor.

```typescript
import type * as Monaco from 'monaco-editor';
import type { CodeIssue } from '$lib/refactoring/types/analysis';

export interface MarkerOptions {
  editor: Monaco.editor.IStandaloneCodeEditor;
  monaco: typeof Monaco;
  issues: CodeIssue[];
}

/**
 * Maps issue severity to Monaco marker severity
 */
function getSeverity(
  monaco: typeof Monaco, 
  severity: CodeIssue['severity']
): Monaco.MarkerSeverity {
  switch (severity) {
    case 'error': return monaco.MarkerSeverity.Error;
    case 'warning': return monaco.MarkerSeverity.Warning;
    case 'suggestion': return monaco.MarkerSeverity.Info;
    default: return monaco.MarkerSeverity.Hint;
  }
}

/**
 * Converts CodeIssue to Monaco marker
 */
function issueToMarker(
  monaco: typeof Monaco,
  issue: CodeIssue
): Monaco.editor.IMarkerData {
  return {
    severity: getSeverity(monaco, issue.severity),
    message: issue.message,
    startLineNumber: issue.line,
    startColumn: issue.column || 1,
    endLineNumber: issue.endLine || issue.line,
    endColumn: issue.endColumn || 1000,
    source: 'VibeForge Analysis',
    code: issue.ruleId
  };
}

/**
 * Sets markers on Monaco editor from analysis issues
 */
export function setAnalysisMarkers({ editor, monaco, issues }: MarkerOptions): void {
  const model = editor.getModel();
  if (!model) return;
  
  const markers = issues
    .filter(issue => issue.line !== undefined)
    .map(issue => issueToMarker(monaco, issue));
  
  monaco.editor.setModelMarkers(model, 'vibeforge-analysis', markers);
}

/**
 * Clears all analysis markers
 */
export function clearAnalysisMarkers(
  monaco: typeof Monaco,
  editor: Monaco.editor.IStandaloneCodeEditor
): void {
  const model = editor.getModel();
  if (!model) return;
  
  monaco.editor.setModelMarkers(model, 'vibeforge-analysis', []);
}

/**
 * Navigates editor to issue location
 */
export function goToIssue(
  editor: Monaco.editor.IStandaloneCodeEditor,
  issue: CodeIssue
): void {
  if (issue.line === undefined) return;
  
  editor.revealLineInCenter(issue.line);
  editor.setPosition({ lineNumber: issue.line, column: issue.column || 1 });
  editor.focus();
}
```

#### 4. analysis.svelte.ts (Store)

```typescript
import { type CodebaseAnalysis, type CodeIssue } from '$lib/refactoring/types/analysis';

interface AnalysisState {
  current: CodebaseAnalysis | null;
  isAnalyzing: boolean;
  error: string | null;
  drawerOpen: boolean;
  drawerMinimized: boolean;
  selectedIssue: CodeIssue | null;
}

function createAnalysisStore() {
  let state = $state<AnalysisState>({
    current: null,
    isAnalyzing: false,
    error: null,
    drawerOpen: false,
    drawerMinimized: false,
    selectedIssue: null
  });
  
  return {
    // Getters
    get current() { return state.current; },
    get isAnalyzing() { return state.isAnalyzing; },
    get error() { return state.error; },
    get drawerOpen() { return state.drawerOpen; },
    get drawerMinimized() { return state.drawerMinimized; },
    get selectedIssue() { return state.selectedIssue; },
    
    get issues() { 
      return state.current?.issues || []; 
    },
    
    get issueCount() {
      if (!state.current) return { errors: 0, warnings: 0, suggestions: 0 };
      const issues = state.current.issues;
      return {
        errors: issues.filter(i => i.severity === 'error').length,
        warnings: issues.filter(i => i.severity === 'warning').length,
        suggestions: issues.filter(i => i.severity === 'suggestion').length
      };
    },
    
    // Actions
    setAnalyzing(value: boolean) {
      state.isAnalyzing = value;
      if (value) state.error = null;
    },
    
    setAnalysis(analysis: CodebaseAnalysis) {
      state.current = analysis;
      state.isAnalyzing = false;
      state.drawerOpen = true;
      state.drawerMinimized = false;
    },
    
    setError(error: string) {
      state.error = error;
      state.isAnalyzing = false;
    },
    
    clearAnalysis() {
      state.current = null;
      state.drawerOpen = false;
      state.selectedIssue = null;
    },
    
    openDrawer() {
      state.drawerOpen = true;
      state.drawerMinimized = false;
    },
    
    closeDrawer() {
      state.drawerOpen = false;
    },
    
    toggleMinimize() {
      state.drawerMinimized = !state.drawerMinimized;
    },
    
    selectIssue(issue: CodeIssue | null) {
      state.selectedIssue = issue;
    }
  };
}

export const analysisStore = createAnalysisStore();
```

#### 5. EditorAnalyzer.ts

Adapter to analyze code from editor (not file system).

```typescript
import type { CodebaseAnalysis, CodeIssue, TechStack } from '../types/analysis';

interface EditorContent {
  content: string;
  language: string;      // 'typescript', 'javascript', 'python', etc.
  filename?: string;     // Optional filename hint
}

interface AnalyzeOptions {
  /** Multiple files (for GitHub repos) */
  files?: Map<string, string>;
  /** Single file content (for pasted code) */
  singleFile?: EditorContent;
}

/**
 * Analyzes code from editor content rather than file system
 */
export class EditorAnalyzer {
  
  /**
   * Analyze single file/snippet pasted into editor
   */
  async analyzeSingleFile(content: EditorContent): Promise<CodebaseAnalysis> {
    const issues: CodeIssue[] = [];
    
    // Detect language if not provided
    const language = content.language || this.detectLanguage(content.content);
    
    // Run language-specific checks
    if (language === 'typescript' || language === 'javascript') {
      issues.push(...this.analyzeJavaScript(content.content));
    } else if (language === 'python') {
      issues.push(...this.analyzePython(content.content));
    }
    
    // Run generic checks
    issues.push(...this.analyzeGeneric(content.content));
    
    // Build analysis result
    return {
      id: `analysis-${Date.now()}`,
      path: content.filename || 'editor',
      analyzedAt: new Date().toISOString(),
      structure: {
        totalFiles: 1,
        sourceFiles: 1,
        testFiles: 0,
        totalDirectories: 0,
        files: [{
          path: content.filename || 'editor.ts',
          relativePath: content.filename || 'editor.ts',
          size: content.content.length,
          extension: this.getExtension(language),
          lines: content.content.split('\n').length
        }]
      },
      techStack: this.detectTechStack(content.content, language),
      metrics: this.calculateMetrics(content.content, issues),
      patterns: [],
      issues,
      summary: this.generateSummary(issues)
    };
  }
  
  /**
   * Analyze multiple files (from GitHub)
   */
  async analyzeMultipleFiles(files: Map<string, string>): Promise<CodebaseAnalysis> {
    const allIssues: CodeIssue[] = [];
    
    for (const [path, content] of files) {
      const language = this.detectLanguageFromPath(path);
      const fileIssues = await this.analyzeSingleFile({
        content,
        language,
        filename: path
      });
      
      // Add file path to each issue
      allIssues.push(...fileIssues.issues.map(issue => ({
        ...issue,
        file: path
      })));
    }
    
    // Aggregate results
    return {
      id: `analysis-${Date.now()}`,
      path: 'repository',
      analyzedAt: new Date().toISOString(),
      structure: {
        totalFiles: files.size,
        sourceFiles: files.size,
        testFiles: [...files.keys()].filter(p => p.includes('.test.') || p.includes('.spec.')).length,
        totalDirectories: new Set([...files.keys()].map(p => p.split('/').slice(0, -1).join('/'))).size,
        files: [...files.entries()].map(([path, content]) => ({
          path,
          relativePath: path,
          size: content.length,
          extension: path.split('.').pop() || '',
          lines: content.split('\n').length
        }))
      },
      techStack: this.detectTechStackFromFiles(files),
      metrics: this.calculateAggregateMetrics(files, allIssues),
      patterns: [],
      issues: allIssues,
      summary: this.generateSummary(allIssues)
    };
  }
  
  /**
   * JavaScript/TypeScript specific analysis
   */
  private analyzeJavaScript(content: string): CodeIssue[] {
    const issues: CodeIssue[] = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      const lineNum = index + 1;
      
      // Check for 'any' type
      if (/:\s*any\b/.test(line)) {
        issues.push({
          id: `any-${lineNum}`,
          severity: 'warning',
          category: 'type-safety',
          ruleId: 'no-explicit-any',
          message: 'Avoid using "any" type - use a specific type instead',
          line: lineNum,
          column: line.indexOf('any') + 1
        });
      }
      
      // Check for var usage
      if (/\bvar\s+\w+/.test(line)) {
        issues.push({
          id: `var-${lineNum}`,
          severity: 'warning',
          category: 'code-quality',
          ruleId: 'no-var',
          message: 'Use "let" or "const" instead of "var"',
          line: lineNum,
          column: line.indexOf('var') + 1
        });
      }
      
      // Check for console.log
      if (/console\.(log|warn|error)/.test(line)) {
        issues.push({
          id: `console-${lineNum}`,
          severity: 'suggestion',
          category: 'code-quality',
          ruleId: 'no-console',
          message: 'Remove console statement before production',
          line: lineNum,
          column: line.indexOf('console') + 1
        });
      }
      
      // Check for TODO comments
      if (/\/\/\s*TODO/i.test(line)) {
        issues.push({
          id: `todo-${lineNum}`,
          severity: 'suggestion',
          category: 'documentation',
          ruleId: 'no-todo',
          message: 'TODO comment found - consider resolving or tracking',
          line: lineNum,
          column: line.indexOf('TODO') + 1
        });
      }
      
      // Check for for...in on arrays
      if (/for\s*\(\s*(var|let|const)\s+\w+\s+in\s+/.test(line)) {
        issues.push({
          id: `for-in-${lineNum}`,
          severity: 'error',
          category: 'code-quality',
          ruleId: 'no-for-in-array',
          message: 'Use "for...of" instead of "for...in" for arrays',
          line: lineNum,
          column: line.indexOf('for') + 1
        });
      }
      
      // Check for == instead of ===
      if (/[^=!]==[^=]/.test(line)) {
        issues.push({
          id: `equality-${lineNum}`,
          severity: 'warning',
          category: 'code-quality',
          ruleId: 'eqeqeq',
          message: 'Use "===" instead of "==" for strict equality',
          line: lineNum,
          column: line.indexOf('==') + 1
        });
      }
      
      // Missing semicolon (basic check)
      const trimmed = line.trim();
      if (trimmed && 
          !trimmed.endsWith(';') && 
          !trimmed.endsWith('{') && 
          !trimmed.endsWith('}') &&
          !trimmed.endsWith(',') &&
          !trimmed.startsWith('//') &&
          !trimmed.startsWith('/*') &&
          !trimmed.startsWith('*') &&
          !trimmed.startsWith('import') &&
          !trimmed.startsWith('export') &&
          /^[\w\s.()[\]]+$/.test(trimmed)) {
        // This is a very basic check - real implementation would use AST
      }
    });
    
    return issues;
  }
  
  /**
   * Python specific analysis
   */
  private analyzePython(content: string): CodeIssue[] {
    const issues: CodeIssue[] = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      const lineNum = index + 1;
      
      // Check for print statements (Python 2 style)
      if (/^print\s+[^(]/.test(line.trim())) {
        issues.push({
          id: `print-${lineNum}`,
          severity: 'error',
          category: 'code-quality',
          ruleId: 'python3-print',
          message: 'Use print() function syntax (Python 3)',
          line: lineNum,
          column: 1
        });
      }
      
      // Check for mutable default arguments
      if (/def\s+\w+\([^)]*=\s*(\[\]|\{\})/.test(line)) {
        issues.push({
          id: `mutable-default-${lineNum}`,
          severity: 'error',
          category: 'code-quality',
          ruleId: 'mutable-default',
          message: 'Mutable default argument - use None and initialize inside function',
          line: lineNum,
          column: 1
        });
      }
    });
    
    return issues;
  }
  
  /**
   * Generic analysis (any language)
   */
  private analyzeGeneric(content: string): CodeIssue[] {
    const issues: CodeIssue[] = [];
    const lines = content.split('\n');
    
    // Check for very long lines
    lines.forEach((line, index) => {
      if (line.length > 120) {
        issues.push({
          id: `long-line-${index + 1}`,
          severity: 'suggestion',
          category: 'code-quality',
          ruleId: 'max-line-length',
          message: `Line exceeds 120 characters (${line.length})`,
          line: index + 1,
          column: 121
        });
      }
    });
    
    // Check for trailing whitespace
    lines.forEach((line, index) => {
      if (/\s+$/.test(line)) {
        issues.push({
          id: `trailing-ws-${index + 1}`,
          severity: 'suggestion',
          category: 'code-quality',
          ruleId: 'no-trailing-whitespace',
          message: 'Trailing whitespace',
          line: index + 1,
          column: line.trimEnd().length + 1
        });
      }
    });
    
    return issues;
  }
  
  private detectLanguage(content: string): string {
    if (content.includes('import React') || content.includes('useState')) return 'typescript';
    if (content.includes('def ') && content.includes(':')) return 'python';
    if (content.includes('func ') && content.includes('->')) return 'swift';
    if (content.includes('fn ') && content.includes('->')) return 'rust';
    if (content.includes('function') || content.includes('=>')) return 'javascript';
    return 'plaintext';
  }
  
  private detectLanguageFromPath(path: string): string {
    const ext = path.split('.').pop()?.toLowerCase();
    const map: Record<string, string> = {
      'ts': 'typescript',
      'tsx': 'typescript',
      'js': 'javascript',
      'jsx': 'javascript',
      'py': 'python',
      'rs': 'rust',
      'go': 'go',
      'swift': 'swift',
      'java': 'java'
    };
    return map[ext || ''] || 'plaintext';
  }
  
  private getExtension(language: string): string {
    const map: Record<string, string> = {
      'typescript': '.ts',
      'javascript': '.js',
      'python': '.py',
      'rust': '.rs'
    };
    return map[language] || '.txt';
  }
  
  private detectTechStack(content: string, language: string): TechStack {
    return {
      language: language,
      framework: this.detectFramework(content),
      buildTool: 'unknown',
      testFramework: 'unknown',
      stateManagement: 'unknown',
      styling: 'unknown'
    };
  }
  
  private detectFramework(content: string): string {
    if (content.includes('import React') || content.includes('from "react"')) return 'React';
    if (content.includes('<script') && content.includes('$:')) return 'Svelte';
    if (content.includes('@Component')) return 'Angular';
    if (content.includes('Vue.component') || content.includes('defineComponent')) return 'Vue';
    if (content.includes('FastAPI') || content.includes('from fastapi')) return 'FastAPI';
    if (content.includes('from django')) return 'Django';
    if (content.includes('express()')) return 'Express';
    return 'unknown';
  }
  
  private detectTechStackFromFiles(files: Map<string, string>): TechStack {
    // Check package.json if present
    const packageJson = files.get('package.json');
    if (packageJson) {
      try {
        const pkg = JSON.parse(packageJson);
        return {
          language: pkg.dependencies?.typescript ? 'TypeScript' : 'JavaScript',
          framework: this.detectFrameworkFromPackage(pkg),
          buildTool: pkg.dependencies?.vite ? 'Vite' : pkg.dependencies?.webpack ? 'Webpack' : 'unknown',
          testFramework: pkg.devDependencies?.vitest ? 'Vitest' : pkg.devDependencies?.jest ? 'Jest' : 'unknown',
          stateManagement: 'unknown',
          styling: pkg.dependencies?.tailwindcss ? 'Tailwind' : 'unknown'
        };
      } catch {}
    }
    
    return {
      language: 'unknown',
      framework: 'unknown',
      buildTool: 'unknown',
      testFramework: 'unknown',
      stateManagement: 'unknown',
      styling: 'unknown'
    };
  }
  
  private detectFrameworkFromPackage(pkg: any): string {
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    if (deps['@sveltejs/kit']) return 'SvelteKit';
    if (deps.svelte) return 'Svelte';
    if (deps.next) return 'Next.js';
    if (deps.react) return 'React';
    if (deps.vue) return 'Vue';
    if (deps['@angular/core']) return 'Angular';
    return 'unknown';
  }
  
  private calculateMetrics(content: string, issues: CodeIssue[]): any {
    const lines = content.split('\n');
    return {
      linesOfCode: lines.length,
      blankLines: lines.filter(l => !l.trim()).length,
      commentLines: lines.filter(l => l.trim().startsWith('//')).length,
      testCoverage: { lines: 0, branches: 0, functions: 0 },
      typeSafety: {
        typedFiles: 0,
        totalFiles: 1,
        percentage: 0,
        anyCount: issues.filter(i => i.ruleId === 'no-explicit-any').length,
        typeErrorCount: 0
      },
      complexity: {
        average: 0,
        max: 0,
        high: []
      }
    };
  }
  
  private calculateAggregateMetrics(files: Map<string, string>, issues: CodeIssue[]): any {
    let totalLines = 0;
    for (const content of files.values()) {
      totalLines += content.split('\n').length;
    }
    
    return {
      linesOfCode: totalLines,
      testCoverage: { lines: 0, branches: 0, functions: 0 },
      typeSafety: {
        typedFiles: 0,
        totalFiles: files.size,
        percentage: 0,
        anyCount: issues.filter(i => i.ruleId === 'no-explicit-any').length,
        typeErrorCount: 0
      }
    };
  }
  
  private generateSummary(issues: CodeIssue[]): any {
    const errors = issues.filter(i => i.severity === 'error').length;
    const warnings = issues.filter(i => i.severity === 'warning').length;
    
    let health: 'excellent' | 'good' | 'fair' | 'poor' = 'excellent';
    if (errors > 0) health = 'poor';
    else if (warnings > 5) health = 'fair';
    else if (warnings > 0) health = 'good';
    
    const score = Math.max(0, 100 - (errors * 10) - (warnings * 3));
    
    return {
      health,
      score,
      criticalIssues: errors,
      recommendations: this.generateRecommendations(issues)
    };
  }
  
  private generateRecommendations(issues: CodeIssue[]): string[] {
    const recommendations: string[] = [];
    
    const categories = new Set(issues.map(i => i.category));
    
    if (categories.has('type-safety')) {
      recommendations.push('Add TypeScript types to improve code reliability');
    }
    if (categories.has('code-quality')) {
      recommendations.push('Fix code quality issues for better maintainability');
    }
    if (issues.some(i => i.ruleId === 'no-console')) {
      recommendations.push('Remove console statements before deployment');
    }
    
    return recommendations;
  }
}

export const editorAnalyzer = new EditorAnalyzer();
```

---

## Part 2: GitHub Integration

### User Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. User clicks [+ GitHub] in left column                            │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. GitHubConnector dialog opens                                     │
│    - Enter URL: https://github.com/user/repo                        │
│    - Select branch (default: main)                                  │
│    - Optional: specify subdirectory                                 │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. For public repos:                                                │
│    - Fetch file tree via GitHub API (no auth)                       │
│    For private repos:                                               │
│    - Redirect to GitHub OAuth                                       │
│    - Get access token                                               │
│    - Fetch file tree with token                                     │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. File tree appears in SourcePanel                                 │
│    - Folders expandable                                             │
│    - Click file → fetches content → loads in editor                 │
│    - Content cached locally (IndexedDB or memory)                   │
└─────────────────────────┬───────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. User clicks [Analyze]                                            │
│    - Fetches all source files (cached if available)                 │
│    - Runs EditorAnalyzer.analyzeMultipleFiles()                     │
│    - Shows results in analysis drawer                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. SourcePanel.svelte

Left column section for managing code sources.

```svelte
<script lang="ts">
  import { sourceStore } from '../stores/source.svelte';
  import GitHubConnector from './GitHubConnector.svelte';
  import FileTree from './FileTree.svelte';
  import SectionHeader from '$lib/ui/primitives/SectionHeader.svelte';
  import Button from '$lib/ui/primitives/Button.svelte';
  
  let showConnector = $state(false);
  
  const connected = $derived(sourceStore.isConnected);
  const repo = $derived(sourceStore.repo);
  const files = $derived(sourceStore.fileTree);
  
  function handleDisconnect() {
    sourceStore.disconnect();
  }
  
  function handleFileSelect(path: string) {
    sourceStore.loadFile(path);
  }
</script>

<div class="source-panel">
  <SectionHeader title="Source" level={3} />
  
  {#if connected && repo}
    <!-- Connected State -->
    <div class="mt-4">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="text-lg">📁</span>
          <div>
            <div class="text-sm font-medium text-slate-200">{repo.name}</div>
            <div class="text-xs text-slate-500">{repo.owner}/{repo.name}</div>
          </div>
        </div>
        <button 
          onclick={handleDisconnect}
          class="text-xs text-slate-500 hover:text-red-400"
        >
          Disconnect
        </button>
      </div>
      
      <FileTree 
        files={files} 
        onSelect={handleFileSelect}
      />
    </div>
  {:else}
    <!-- Empty State -->
    <div class="mt-4 space-y-3">
      <p class="text-sm text-slate-400">
        Connect a repository or upload files to analyze
      </p>
      
      <div class="space-y-2">
        <Button 
          variant="secondary" 
          size="sm" 
          class="w-full justify-start"
          onclick={() => showConnector = true}
        >
          <span class="mr-2">🔗</span> Connect GitHub
        </Button>
        
        <Button 
          variant="secondary" 
          size="sm" 
          class="w-full justify-start"
          onclick={() => {/* TODO: file upload */}}
        >
          <span class="mr-2">📁</span> Upload Files
        </Button>
      </div>
    </div>
  {/if}
</div>

{#if showConnector}
  <GitHubConnector 
    onConnect={() => showConnector = false}
    onCancel={() => showConnector = false}
  />
{/if}
```

#### 2. GitHubConnector.svelte

Dialog for connecting to GitHub repository.

```svelte
<script lang="ts">
  import { sourceStore } from '../stores/source.svelte';
  import Modal from '$lib/ui/primitives/Modal.svelte';
  import Input from '$lib/ui/primitives/Input.svelte';
  import Button from '$lib/ui/primitives/Button.svelte';
  
  interface Props {
    onConnect?: () => void;
    onCancel?: () => void;
  }
  
  let { onConnect, onCancel }: Props = $props();
  
  let url = $state('');
  let branch = $state('main');
  let subdirectory = $state('');
  let isPrivate = $state(false);
  let isLoading = $state(false);
  let error = $state<string | null>(null);
  
  // Parse GitHub URL
  const parsed = $derived(() => {
    const match = url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (match) {
      return { owner: match[1], repo: match[2].replace('.git', '') };
    }
    return null;
  });
  
  const isValid = $derived(parsed() !== null);
  
  async function handleConnect() {
    const info = parsed();
    if (!info) return;
    
    isLoading = true;
    error = null;
    
    try {
      await sourceStore.connect({
        owner: info.owner,
        repo: info.repo,
        branch,
        subdirectory: subdirectory || undefined,
        isPrivate
      });
      
      onConnect?.();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to connect';
    } finally {
      isLoading = false;
    }
  }
  
  async function handleOAuth() {
    // TODO: Implement GitHub OAuth flow
    // For now, just set isPrivate flag
    isPrivate = true;
  }
</script>

<Modal title="Connect GitHub Repository" onClose={onCancel}>
  <div class="space-y-4 p-4">
    <!-- URL Input -->
    <div>
      <Input
        bind:value={url}
        label="Repository URL"
        placeholder="https://github.com/owner/repo"
      />
      {#if parsed()}
        <p class="mt-1 text-xs text-green-400">
          ✓ {parsed().owner}/{parsed().repo}
        </p>
      {/if}
    </div>
    
    <!-- Branch -->
    <div>
      <Input
        bind:value={branch}
        label="Branch"
        placeholder="main"
      />
    </div>
    
    <!-- Subdirectory (optional) -->
    <div>
      <Input
        bind:value={subdirectory}
        label="Subdirectory (optional)"
        placeholder="src/lib"
      />
    </div>
    
    <!-- Private repo toggle -->
    <div class="flex items-center gap-3">
      <input 
        type="checkbox" 
        id="private" 
        bind:checked={isPrivate}
        class="rounded border-slate-600"
      />
      <label for="private" class="text-sm text-slate-300">
        Private repository
      </label>
    </div>
    
    {#if isPrivate}
      <Button variant="secondary" onclick={handleOAuth} class="w-full">
        🔑 Authorize with GitHub
      </Button>
    {/if}
    
    <!-- Error -->
    {#if error}
      <div class="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
        {error}
      </div>
    {/if}
    
    <!-- Actions -->
    <div class="flex justify-end gap-3 pt-4 border-t border-slate-700">
      <Button variant="ghost" onclick={onCancel}>
        Cancel
      </Button>
      <Button 
        variant="primary" 
        onclick={handleConnect}
        disabled={!isValid || isLoading}
      >
        {isLoading ? 'Connecting...' : 'Connect'}
      </Button>
    </div>
  </div>
</Modal>
```

#### 3. FileTree.svelte

Displays repository file structure.

```svelte
<script lang="ts">
  import type { FileTreeNode } from '../stores/source.svelte';
  import FileTreeItem from './FileTreeItem.svelte';
  
  interface Props {
    files: FileTreeNode[];
    onSelect?: (path: string) => void;
  }
  
  let { files, onSelect }: Props = $props();
</script>

<div class="file-tree text-sm">
  {#each files as node (node.path)}
    <FileTreeItem {node} {onSelect} depth={0} />
  {/each}
</div>

<style>
  .file-tree {
    max-height: 400px;
    overflow-y: auto;
  }
</style>
```

#### 4. FileTreeItem.svelte

Individual file/folder in tree.

```svelte
<script lang="ts">
  import type { FileTreeNode } from '../stores/source.svelte';
  
  interface Props {
    node: FileTreeNode;
    depth: number;
    onSelect?: (path: string) => void;
  }
  
  let { node, depth, onSelect }: Props = $props();
  
  let expanded = $state(depth < 2); // Auto-expand first 2 levels
  
  const icon = $derived(
    node.type === 'directory' 
      ? (expanded ? '📂' : '📁')
      : getFileIcon(node.name)
  );
  
  function getFileIcon(name: string): string {
    if (name.endsWith('.ts') || name.endsWith('.tsx')) return '🔷';
    if (name.endsWith('.js') || name.endsWith('.jsx')) return '🟨';
    if (name.endsWith('.svelte')) return '🟠';
    if (name.endsWith('.json')) return '📋';
    if (name.endsWith('.md')) return '📝';
    if (name.endsWith('.css')) return '🎨';
    return '📄';
  }
  
  function handleClick() {
    if (node.type === 'directory') {
      expanded = !expanded;
    } else {
      onSelect?.(node.path);
    }
  }
</script>

<div>
  <button
    class="w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-slate-700/50 text-left"
    style="padding-left: {depth * 12 + 8}px"
    onclick={handleClick}
  >
    <span class="text-xs">{icon}</span>
    <span class="truncate text-slate-300">{node.name}</span>
  </button>
  
  {#if node.type === 'directory' && expanded && node.children}
    {#each node.children as child (child.path)}
      <svelte:self node={child} depth={depth + 1} {onSelect} />
    {/each}
  {/if}
</div>
```

#### 5. source.svelte.ts (Store)

```typescript
interface RepoInfo {
  owner: string;
  repo: string;
  branch: string;
  subdirectory?: string;
  name: string;
}

export interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileTreeNode[];
}

interface ConnectOptions {
  owner: string;
  repo: string;
  branch: string;
  subdirectory?: string;
  isPrivate?: boolean;
}

interface SourceState {
  repo: RepoInfo | null;
  fileTree: FileTreeNode[];
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  
  // File cache (path -> content)
  fileCache: Map<string, string>;
  
  // Currently loaded file
  currentFile: string | null;
}

function createSourceStore() {
  let state = $state<SourceState>({
    repo: null,
    fileTree: [],
    isConnected: false,
    isLoading: false,
    error: null,
    fileCache: new Map(),
    currentFile: null
  });
  
  // GitHub API base URL
  const API_BASE = 'https://api.github.com';
  
  return {
    // Getters
    get repo() { return state.repo; },
    get fileTree() { return state.fileTree; },
    get isConnected() { return state.isConnected; },
    get isLoading() { return state.isLoading; },
    get error() { return state.error; },
    get currentFile() { return state.currentFile; },
    
    /**
     * Connect to a GitHub repository
     */
    async connect(options: ConnectOptions) {
      state.isLoading = true;
      state.error = null;
      
      try {
        // Fetch repo info
        const repoRes = await fetch(
          `${API_BASE}/repos/${options.owner}/${options.repo}`
        );
        
        if (!repoRes.ok) {
          throw new Error(repoRes.status === 404 
            ? 'Repository not found' 
            : 'Failed to fetch repository'
          );
        }
        
        // Fetch file tree
        const treePath = options.subdirectory 
          ? `${options.branch}:${options.subdirectory}`
          : options.branch;
          
        const treeRes = await fetch(
          `${API_BASE}/repos/${options.owner}/${options.repo}/git/trees/${treePath}?recursive=1`
        );
        
        if (!treeRes.ok) {
          throw new Error('Failed to fetch file tree');
        }
        
        const treeData = await treeRes.json();
        
        // Build tree structure
        state.fileTree = this.buildFileTree(treeData.tree, options.subdirectory);
        
        state.repo = {
          owner: options.owner,
          repo: options.repo,
          branch: options.branch,
          subdirectory: options.subdirectory,
          name: options.repo
        };
        
        state.isConnected = true;
        
      } catch (e) {
        state.error = e instanceof Error ? e.message : 'Connection failed';
        throw e;
      } finally {
        state.isLoading = false;
      }
    },
    
    /**
     * Disconnect from repository
     */
    disconnect() {
      state.repo = null;
      state.fileTree = [];
      state.isConnected = false;
      state.fileCache.clear();
      state.currentFile = null;
    },
    
    /**
     * Load a file's content
     */
    async loadFile(path: string): Promise<string> {
      // Check cache first
      if (state.fileCache.has(path)) {
        state.currentFile = path;
        return state.fileCache.get(path)!;
      }
      
      if (!state.repo) {
        throw new Error('No repository connected');
      }
      
      const fullPath = state.repo.subdirectory 
        ? `${state.repo.subdirectory}/${path}`
        : path;
      
      const res = await fetch(
        `${API_BASE}/repos/${state.repo.owner}/${state.repo.repo}/contents/${fullPath}?ref=${state.repo.branch}`
      );
      
      if (!res.ok) {
        throw new Error('Failed to fetch file');
      }
      
      const data = await res.json();
      const content = atob(data.content);
      
      // Cache it
      state.fileCache.set(path, content);
      state.currentFile = path;
      
      return content;
    },
    
    /**
     * Get all cached files (for analysis)
     */
    getCachedFiles(): Map<string, string> {
      return state.fileCache;
    },
    
    /**
     * Fetch all source files for analysis
     */
    async fetchAllSourceFiles(): Promise<Map<string, string>> {
      if (!state.repo) {
        throw new Error('No repository connected');
      }
      
      const sourceFiles = this.getSourceFilePaths(state.fileTree);
      
      // Fetch files not in cache (in parallel, with limit)
      const uncached = sourceFiles.filter(p => !state.fileCache.has(p));
      const batchSize = 10;
      
      for (let i = 0; i < uncached.length; i += batchSize) {
        const batch = uncached.slice(i, i + batchSize);
        await Promise.all(batch.map(p => this.loadFile(p)));
      }
      
      return state.fileCache;
    },
    
    /**
     * Build file tree from GitHub API response
     */
    buildFileTree(items: any[], basePath?: string): FileTreeNode[] {
      const root: FileTreeNode[] = [];
      const map = new Map<string, FileTreeNode>();
      
      // Filter to relevant paths
      const filtered = items.filter(item => {
        // Skip non-source files
        if (item.type === 'blob') {
          const ext = item.path.split('.').pop();
          return ['ts', 'tsx', 'js', 'jsx', 'svelte', 'py', 'rs', 'go', 'java', 'json', 'md'].includes(ext);
        }
        return item.type === 'tree';
      });
      
      // Build tree
      for (const item of filtered) {
        const pathParts = item.path.split('/');
        const name = pathParts[pathParts.length - 1];
        
        const node: FileTreeNode = {
          name,
          path: item.path,
          type: item.type === 'tree' ? 'directory' : 'file',
          children: item.type === 'tree' ? [] : undefined
        };
        
        map.set(item.path, node);
        
        if (pathParts.length === 1) {
          root.push(node);
        } else {
          const parentPath = pathParts.slice(0, -1).join('/');
          const parent = map.get(parentPath);
          if (parent && parent.children) {
            parent.children.push(node);
          }
        }
      }
      
      return root;
    },
    
    /**
     * Get paths of source files from tree
     */
    getSourceFilePaths(nodes: FileTreeNode[]): string[] {
      const paths: string[] = [];
      
      function walk(node: FileTreeNode) {
        if (node.type === 'file') {
          paths.push(node.path);
        } else if (node.children) {
          node.children.forEach(walk);
        }
      }
      
      nodes.forEach(walk);
      return paths;
    }
  };
}

export const sourceStore = createSourceStore();
```

---

## Part 3: Wiring It Together

### Updated PromptEditor Integration

```svelte
<!-- In PromptEditor.svelte - add marker support -->
<script lang="ts">
  import { analysisStore } from '../stores/analysis.svelte';
  import { setAnalysisMarkers, clearAnalysisMarkers, goToIssue } from '../analysis/MonacoMarkers';
  
  // ... existing code ...
  
  let monacoInstance: typeof Monaco | null = null;
  let editorInstance: Monaco.editor.IStandaloneCodeEditor | null = null;
  
  // Watch for analysis changes and update markers
  $effect(() => {
    if (monacoInstance && editorInstance && analysisStore.current) {
      setAnalysisMarkers({
        monaco: monacoInstance,
        editor: editorInstance,
        issues: analysisStore.issues
      });
    }
  });
  
  // Handle issue selection (from drawer)
  $effect(() => {
    if (editorInstance && analysisStore.selectedIssue) {
      goToIssue(editorInstance, analysisStore.selectedIssue);
    }
  });
  
  function handleEditorMount(editor: Monaco.editor.IStandaloneCodeEditor, monaco: typeof Monaco) {
    editorInstance = editor;
    monacoInstance = monaco;
  }
</script>
```

### Updated Main Layout

```svelte
<!-- In main workbench layout -->
<script lang="ts">
  import { ContextColumn } from '$lib/workbench/context';
  import { PromptColumn } from '$lib/workbench/prompt';
  import { OutputColumn } from '$lib/workbench/output';
  import { SourcePanel } from '$lib/workbench/source';
  import { AnalysisDrawer } from '$lib/workbench/analysis';
  import { analysisStore } from '$lib/workbench/stores/analysis.svelte';
  import { sourceStore } from '$lib/workbench/stores/source.svelte';
  import { editorAnalyzer } from '$lib/refactoring/analyzer/EditorAnalyzer';
  import { promptStore } from '$lib/core/stores';
  
  async function handleAnalyze() {
    analysisStore.setAnalyzing(true);
    
    try {
      let analysis;
      
      if (sourceStore.isConnected) {
        // Analyze connected repo
        const files = await sourceStore.fetchAllSourceFiles();
        analysis = await editorAnalyzer.analyzeMultipleFiles(files);
      } else {
        // Analyze editor content
        const content = promptStore.text;
        analysis = await editorAnalyzer.analyzeSingleFile({
          content,
          language: 'typescript' // TODO: detect from content
        });
      }
      
      analysisStore.setAnalysis(analysis);
    } catch (e) {
      analysisStore.setError(e instanceof Error ? e.message : 'Analysis failed');
    }
  }
  
  function handleGeneratePlan() {
    // TODO: Generate refactoring plan from analysis
  }
  
  function handleAddFeature() {
    // TODO: Open feature planner
  }
</script>

<div class="workbench-layout h-screen flex flex-col">
  <!-- Top Bar -->
  <header class="h-12 border-b border-slate-700 flex items-center justify-between px-4">
    <div class="flex items-center gap-4">
      <!-- Logo, etc -->
    </div>
    <div class="flex items-center gap-2">
      <button 
        class="px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        onclick={handleAnalyze}
        disabled={analysisStore.isAnalyzing}
      >
        {analysisStore.isAnalyzing ? 'Analyzing...' : 'Analyze'}
      </button>
      <button class="px-4 py-1.5 bg-forge-ember text-white rounded-lg">
        Run Prompt
      </button>
    </div>
  </header>
  
  <!-- Main Content -->
  <div class="flex-1 flex overflow-hidden">
    <!-- Left Column -->
    <aside class="w-72 border-r border-slate-700 flex flex-col overflow-hidden">
      <div class="flex-1 overflow-y-auto p-4 space-y-6">
        <ContextColumn />
        <SourcePanel />
      </div>
    </aside>
    
    <!-- Center + Right (with drawer) -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="flex-1 flex overflow-hidden">
        <!-- Center: Editor -->
        <main class="flex-1 overflow-hidden">
          <PromptColumn />
        </main>
        
        <!-- Right: Output -->
        <aside class="w-96 border-l border-slate-700 overflow-hidden">
          <OutputColumn />
        </aside>
      </div>
      
      <!-- Bottom: Analysis Drawer -->
      <AnalysisDrawer 
        onClose={() => analysisStore.closeDrawer()}
        onGeneratePlan={handleGeneratePlan}
        onAddFeature={handleAddFeature}
      />
    </div>
  </div>
</div>
```

---

## Database Schema

For persistent storage (DataForge):

```sql
-- Store connected repositories
CREATE TABLE connected_repos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  owner VARCHAR(255) NOT NULL,
  repo VARCHAR(255) NOT NULL,
  branch VARCHAR(255) DEFAULT 'main',
  subdirectory VARCHAR(500),
  connected_at TIMESTAMPTZ DEFAULT NOW(),
  last_accessed TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(user_id, owner, repo)
);

-- Cache file contents
CREATE TABLE file_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id UUID NOT NULL REFERENCES connected_repos(id) ON DELETE CASCADE,
  path VARCHAR(1000) NOT NULL,
  content TEXT NOT NULL,
  sha VARCHAR(40),
  cached_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(repo_id, path)
);

-- Store analysis results
CREATE TABLE analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  repo_id UUID REFERENCES connected_repos(id),
  analyzed_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Summary
  health VARCHAR(20),
  score INTEGER,
  error_count INTEGER,
  warning_count INTEGER,
  suggestion_count INTEGER,
  
  -- Full results (JSON)
  results JSONB NOT NULL
);

CREATE INDEX idx_analysis_user ON analysis_results(user_id);
CREATE INDEX idx_analysis_repo ON analysis_results(repo_id);
```

---

## Implementation Phases

### Phase 1: Analysis UI Foundation (~2 hours)

1. Create `src/lib/workbench/analysis/` directory
2. Implement `analysis.svelte.ts` store
3. Implement `AnalysisDrawer.svelte`
4. Implement `IssueList.svelte` and `IssueItem.svelte`
5. Implement `AnalysisSummary.svelte`

### Phase 2: Monaco Markers (~1 hour)

1. Implement `MonacoMarkers.ts`
2. Update `MonacoEditor.svelte` to expose monaco instance
3. Wire markers to analysis store
4. Test inline squiggles

### Phase 3: Editor Analyzer (~2 hours)

1. Create `EditorAnalyzer.ts`
2. Implement single-file analysis
3. Implement multi-file analysis
4. Add language-specific checks (JS/TS, Python)
5. Add generic checks

### Phase 4: GitHub Integration (~3 hours)

1. Create `src/lib/workbench/source/` directory
2. Implement `source.svelte.ts` store
3. Implement `GitHubConnector.svelte`
4. Implement `SourcePanel.svelte`
5. Implement `FileTree.svelte` and `FileTreeItem.svelte`
6. Test public repo connection

### Phase 5: Wire Everything Together (~2 hours)

1. Update main workbench layout
2. Add [Analyze] button to top bar
3. Wire SourcePanel to ContextColumn area
4. Connect analysis to editor markers
5. Handle file selection → editor load

### Phase 6: Polish & Tests (~2 hours)

1. Add loading states
2. Add error handling
3. Write tests for EditorAnalyzer
4. Write tests for stores
5. Test full flow

---

## Claude Code Prompt

```
You are implementing Code Analysis and GitHub Integration for VibeForge. This adds the ability to:
1. Analyze code pasted in the editor (find issues, suggest fixes)
2. Connect to GitHub repositories and browse/analyze them
3. Display inline markers in Monaco editor
4. Show analysis results in a collapsible drawer

## Project Context
- Framework: SvelteKit with Svelte 5 runes ($state, $derived, $effect)
- Styling: Tailwind CSS
- Editor: Monaco (already integrated at src/lib/ui/primitives/MonacoEditor.svelte)
- Existing analyzer: src/lib/refactoring/analyzer/ (for file system, needs adapter for editor content)

## Key Files to Reference
- src/lib/ui/primitives/MonacoEditor.svelte - Existing Monaco wrapper
- src/lib/refactoring/analyzer/CodebaseAnalyzer.ts - Existing analyzer
- src/lib/refactoring/types/analysis.ts - Analysis types
- src/lib/core/stores/index.ts - Store patterns

---

### PHASE 1: Analysis Store & Components (~2 hours)

#### Step 1.1: Create analysis store
**File:** `src/lib/workbench/stores/analysis.svelte.ts`

[Include full store code from document]

#### Step 1.2: Create AnalysisDrawer
**File:** `src/lib/workbench/analysis/AnalysisDrawer.svelte`

[Include full component code]

#### Step 1.3: Create IssueList and IssueItem
**Files:** 
- `src/lib/workbench/analysis/IssueList.svelte`
- `src/lib/workbench/analysis/IssueItem.svelte`

#### Step 1.4: Create barrel export
**File:** `src/lib/workbench/analysis/index.ts`

```typescript
export { default as AnalysisDrawer } from './AnalysisDrawer.svelte';
export { default as AnalysisSummary } from './AnalysisSummary.svelte';
export { default as IssueList } from './IssueList.svelte';
export { default as IssueItem } from './IssueItem.svelte';
export * from './MonacoMarkers';
```

**Verify:** `pnpm check`

---

### PHASE 2: Monaco Markers (~1 hour)

#### Step 2.1: Create MonacoMarkers utility
**File:** `src/lib/workbench/analysis/MonacoMarkers.ts`

[Include full utility code]

#### Step 2.2: Update MonacoEditor to expose instances
**File:** `src/lib/ui/primitives/MonacoEditor.svelte`

Add props:
```typescript
export let onEditorMount: ((editor: Monaco.editor.IStandaloneCodeEditor, monaco: typeof Monaco) => void) | undefined = undefined;
```

Call in onMount after editor creation:
```typescript
if (onEditorMount) {
  onEditorMount(editor, monaco);
}
```

**Verify:** `pnpm check`

---

### PHASE 3: Editor Analyzer (~2 hours)

#### Step 3.1: Create EditorAnalyzer
**File:** `src/lib/refactoring/analyzer/EditorAnalyzer.ts`

[Include full analyzer code]

**Verify:** `pnpm check && pnpm test`

---

### PHASE 4: GitHub Integration (~3 hours)

#### Step 4.1: Create source store
**File:** `src/lib/workbench/stores/source.svelte.ts`

[Include full store code]

#### Step 4.2: Create GitHubConnector
**File:** `src/lib/workbench/source/GitHubConnector.svelte`

[Include full component code]

#### Step 4.3: Create SourcePanel
**File:** `src/lib/workbench/source/SourcePanel.svelte`

[Include full component code]

#### Step 4.4: Create FileTree components
**Files:**
- `src/lib/workbench/source/FileTree.svelte`
- `src/lib/workbench/source/FileTreeItem.svelte`

#### Step 4.5: Create barrel export
**File:** `src/lib/workbench/source/index.ts`

```typescript
export { default as SourcePanel } from './SourcePanel.svelte';
export { default as GitHubConnector } from './GitHubConnector.svelte';
export { default as FileTree } from './FileTree.svelte';
export { default as FileTreeItem } from './FileTreeItem.svelte';
```

**Verify:** `pnpm check`

---

### PHASE 5: Integration (~2 hours)

#### Step 5.1: Add SourcePanel to left column
Update `src/lib/workbench/context/ContextColumn.svelte` to include SourcePanel below context blocks.

#### Step 5.2: Add Analyze button to top bar
Update the main layout to include [Analyze] button that triggers analysis.

#### Step 5.3: Add AnalysisDrawer to layout
Add drawer below main content area.

#### Step 5.4: Wire analysis to Monaco markers
Update PromptEditor to apply markers when analysis changes.

**Verify:** `pnpm check && pnpm build`

---

### PHASE 6: Tests (~2 hours)

Create test files:
- `src/lib/refactoring/analyzer/EditorAnalyzer.test.ts`
- `src/lib/workbench/stores/analysis.test.ts`
- `src/lib/workbench/stores/source.test.ts`

**Verify:** `pnpm test:coverage` - ensure 100% coverage on new code

---

### FINAL: Verification

```bash
pnpm check
pnpm test
pnpm build

git add -A
git commit -m "feat: Add code analysis UI and GitHub integration"
```

---

## Success Criteria

- [ ] Can paste code in editor and click [Analyze]
- [ ] Issues appear as inline squiggles in Monaco
- [ ] Analysis drawer shows issue list grouped by severity
- [ ] Can click issue to jump to line in editor
- [ ] Can connect to public GitHub repo
- [ ] File tree appears in left column
- [ ] Can click file to load in editor
- [ ] Can analyze entire repo
- [ ] 100% test coverage on new code

---

Begin execution. Start with Phase 1, Step 1.1.
```

---

## Summary

| Component | AI Time | Description |
|-----------|---------|-------------|
| Analysis UI | ~3h | Drawer, issue list, markers |
| Editor Analyzer | ~2h | Analyze editor content |
| GitHub Integration | ~3h | Connect, browse, cache |
| Integration | ~2h | Wire everything together |
| Tests | ~2h | Full coverage |
| **Total** | **~12h** | Complete feature |

---

## Files Created/Modified

### New Files
```
src/lib/workbench/
├── analysis/
│   ├── AnalysisDrawer.svelte
│   ├── AnalysisSummary.svelte
│   ├── IssueList.svelte
│   ├── IssueItem.svelte
│   ├── MonacoMarkers.ts
│   └── index.ts
├── source/
│   ├── SourcePanel.svelte
│   ├── GitHubConnector.svelte
│   ├── FileTree.svelte
│   ├── FileTreeItem.svelte
│   └── index.ts
└── stores/
    ├── analysis.svelte.ts
    ├── source.svelte.ts
    └── index.ts

src/lib/refactoring/analyzer/
└── EditorAnalyzer.ts
```

### Modified Files
```
src/lib/ui/primitives/MonacoEditor.svelte  (add onEditorMount prop)
src/lib/workbench/prompt/PromptEditor.svelte  (wire markers)
src/routes/+page.svelte or main layout  (add drawer, analyze button)
```
