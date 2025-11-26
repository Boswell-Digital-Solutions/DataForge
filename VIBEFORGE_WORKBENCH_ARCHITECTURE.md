# VibeForge Workbench-Primary Architecture

## Implementation Guide v1.0

**Date:** November 24, 2025  
**Status:** Ready for Implementation  
**Architecture Decision:** Workbench-Primary with Modal Wizard

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Implementation Prompt for Claude](#3-implementation-prompt-for-claude)
4. [Phase 1: Foundation](#4-phase-1-foundation)
5. [Phase 2: Modal Wizard Component](#5-phase-2-modal-wizard-component)
6. [Phase 3: Data Handoff](#6-phase-3-data-handoff)
7. [Phase 4: Power User Flow](#7-phase-4-power-user-flow)
8. [Type Definitions](#8-type-definitions)
9. [Store Implementations](#9-store-implementations)
10. [Component Specifications](#10-component-specifications)
11. [Testing Strategy](#11-testing-strategy)
12. [Migration Checklist](#12-migration-checklist)

---

## 1. Executive Summary

### The Decision

VibeForge will adopt a **workbench-primary architecture** where:

- The **workbench** (3-column prompt engineering layout) is the core product
- The **wizard** becomes a modal overlay that teaches workbench concepts
- **Power users** can skip the wizard entirely via Quick Create or keyboard shortcuts
- Both paths lead to the same destination: a fully initialized workbench

### Why This Approach

| Factor | Benefit |
|--------|---------|
| **Clear Product Identity** | "VS Code of prompt engineering" - one tool, not two |
| **Unified Development** | All investment goes into core workbench excellence |
| **Natural Skill Progression** | Wizard teaches → Workbench mastery |
| **Reduced Maintenance** | One UX pattern + modal flow (not two separate apps) |
| **Better Analytics** | Single user journey to optimize |

### Estimated Effort

- **Phase 1 (Foundation):** 20 hours
- **Phase 2 (Modal Wizard):** 25 hours
- **Phase 3 (Data Handoff):** 20 hours
- **Phase 4 (Power User Flow):** 15 hours
- **Testing & Polish:** 20 hours
- **Total:** ~100 hours (2.5 weeks)

---

## 2. Architecture Overview

### Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VIBEFORGE PRODUCT                                    │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    WORKBENCH (Core Product)                      │   │
│   │                                                                  │   │
│   │   ┌─────────┐    ┌─────────────┐    ┌──────────────┐            │   │
│   │   │ Context │    │   Prompt    │    │    Output    │            │   │
│   │   │  Panel  │    │   Editor    │    │    Panel     │            │   │
│   │   └─────────┘    └─────────────┘    └──────────────┘            │   │
│   │                                                                  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ▲                                           │
│                              │                                           │
│   ┌──────────────────────────┴──────────────────────────────────────┐   │
│   │              WIZARD (Guided Onboarding Modal)                    │   │
│   │                                                                  │   │
│   │   Step 1 ──► Step 2 ──► Step 3 ──► Step 4 ──► Step 5            │   │
│   │   Intent     Languages   Stack      Config      Launch           │   │
│   │                                                    │             │   │
│   │                                         Opens workbench          │   │
│   │                                         with project loaded      │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### User Journey

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER JOURNEYS                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  NEW USER:                                                           │
│  Landing ──► Welcome Overlay ──► Wizard Modal ──► Workbench         │
│                                                                      │
│  RETURNING USER (with recent projects):                              │
│  Landing ──► Click Recent Project ──► Workbench (project loaded)    │
│                                                                      │
│  POWER USER:                                                         │
│  Landing ──► ⌘N ──► Quick Create ──► Workbench                      │
│         or                                                           │
│  Landing ──► ⌘K ──► "New from Template" ──► Workbench               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Target File Structure

```
src/lib/
├── workbench/                      # ← PRIMARY PRODUCT
│   ├── components/
│   │   ├── WorkbenchShell.svelte   # Main 3-column layout
│   │   ├── ContextPanel.svelte     # Left column
│   │   ├── PromptEditor.svelte     # Center column
│   │   ├── OutputPanel.svelte      # Right column
│   │   ├── TopBar.svelte           # Header with project info
│   │   ├── StatusBar.svelte        # Footer with status
│   │   ├── WelcomeOverlay.svelte   # First-visit experience
│   │   ├── CommandPalette.svelte   # ⌘K command interface
│   │   │
│   │   ├── NewProjectWizard/       # ← MODAL WIZARD
│   │   │   ├── NewProjectWizard.svelte
│   │   │   ├── WizardOverlay.svelte
│   │   │   ├── WizardProgress.svelte
│   │   │   ├── steps/
│   │   │   │   ├── StepIntent.svelte
│   │   │   │   ├── StepLanguages.svelte
│   │   │   │   ├── StepStack.svelte
│   │   │   │   ├── StepConfig.svelte
│   │   │   │   └── StepLaunch.svelte
│   │   │   └── index.ts
│   │   │
│   │   └── QuickCreate/            # ← POWER USER FLOW
│   │       ├── QuickCreateDialog.svelte
│   │       └── index.ts
│   │
│   ├── stores/                     # Svelte 5 runes stores
│   │   ├── wizard.svelte.ts        # Wizard state
│   │   ├── project.svelte.ts       # Active project state
│   │   └── userPreferences.svelte.ts
│   │
│   └── types/
│       ├── wizard.ts
│       ├── project.ts
│       └── index.ts
│
├── core/                           # ← SHARED INFRASTRUCTURE
│   ├── stores/                     # Existing V2 stores (keep)
│   │   ├── workspace.svelte.ts
│   │   ├── contextBlocks.svelte.ts
│   │   ├── prompt.svelte.ts
│   │   ├── models.svelte.ts
│   │   └── runs.svelte.ts
│   │
│   └── types/
│       └── index.ts
│
├── shared/                         # ← SHARED COMPONENTS
│   ├── ui/
│   │   ├── Button.svelte
│   │   ├── Input.svelte
│   │   ├── Modal.svelte
│   │   └── ...
│   └── utils/
│       └── ...
│
├── api/                            # ← API CLIENTS (keep)
│   ├── vibeforgeClient.ts
│   ├── languagesClient.ts
│   └── stackProfilesClient.ts
│
└── stores/                         # ← LEGACY (migrate or remove)
    ├── wizardStore.ts              # → Migrate to workbench/stores/wizard.svelte.ts
    ├── languagesStore.ts           # → Keep (shared)
    └── stacksStore.ts              # → Keep (shared)

src/routes/
├── +page.svelte                    # → Renders WorkbenchShell
├── +layout.svelte                  # App layout
├── analytics/                      # Keep as-is
├── settings/                       # Keep as-is
└── wizard/                         # → REMOVE (wizard becomes modal)
```

---

## 3. Implementation Prompt for Claude

Copy this prompt to start the refactoring in VS Code with Claude:

```
# VibeForge Workbench-Primary Refactoring

## Context

I'm refactoring VibeForge from a dual-product architecture (wizard + workbench as separate routes) to a workbench-primary architecture where:

1. The workbench (3-column prompt engineering layout) is the CORE product
2. The wizard becomes a MODAL overlay within the workbench
3. Power users can skip the wizard via Quick Create (⌘N) or Command Palette (⌘K)

## Current State

- `/routes/wizard/` contains a 5-step wizard flow (71% complete)
- `/routes/+page.svelte` has an incomplete workbench
- Two state systems: old `writable` stores in `/lib/stores/` and new Svelte 5 runes in `/lib/core/stores/`
- V2 workbench stores exist but aren't fully wired to UI

## Target State

1. Single route (`/`) renders `WorkbenchShell.svelte`
2. Wizard is a modal component (`NewProjectWizard.svelte`) that overlays the workbench
3. All state management uses Svelte 5 runes (`.svelte.ts` files)
4. Wizard completion initializes workbench with project context
5. Power users have Quick Create dialog and keyboard shortcuts

## Implementation Order

### Phase 1: Foundation (Do First)
1. Create the new file structure under `src/lib/workbench/`
2. Create type definitions in `src/lib/workbench/types/`
3. Create `wizard.svelte.ts` store with Svelte 5 runes
4. Create `project.svelte.ts` store for active project management
5. Create `userPreferences.svelte.ts` for power user settings

### Phase 2: Modal Wizard
1. Create `NewProjectWizard.svelte` as a modal component
2. Create `WizardProgress.svelte` for step indicators
3. Migrate existing step components from `/routes/wizard/` to modal steps
4. Wire wizard store to step components
5. Add keyboard shortcuts (Escape to close, ⌘↵ to proceed)

### Phase 3: Data Handoff
1. Implement `projectStore.createFromWizard()` function
2. Create `initializeWorkbenchFromProject()` to set up:
   - Workspace store
   - Initial context blocks from project data
   - Initial prompt template
   - Language-specific patterns
3. Wire wizard completion to workbench initialization
4. Add learning integration (track project creation)

### Phase 4: Power User Flow
1. Create `QuickCreateDialog.svelte` for minimal project creation
2. Create `CommandPalette.svelte` for ⌘K interface
3. Create `WelcomeOverlay.svelte` for first-visit experience
4. Add keyboard shortcuts to `WorkbenchShell.svelte`
5. Implement user preference for "skip wizard"

### Phase 5: Cleanup
1. Remove `/routes/wizard/` directory
2. Migrate any remaining old stores to Svelte 5 runes
3. Update `/routes/+page.svelte` to render `WorkbenchShell`
4. Update navigation and any links to wizard

## Key Technical Requirements

1. **Svelte 5 Runes**: All new stores must use `$state`, `$derived`, `$effect`
2. **TypeScript**: Full type coverage, no `any` types
3. **Tailwind**: Use existing Forge design system (gunmetal, blacksteel, ember colors)
4. **Tauri**: Project generation uses `invoke('generate_project', {...})`
5. **Learning**: Track wizard/project data via `vibeforgeClient`

## Reference: Architecture Document

I have a detailed architecture document with:
- Complete type definitions
- Full store implementations
- Component specifications
- Data flow diagrams

Please read the VIBEFORGE_WORKBENCH_ARCHITECTURE.md file in the project root for complete specifications.

## Starting Point

Let's begin with Phase 1. Please:

1. Review the existing codebase structure
2. Create the new directory structure under `src/lib/workbench/`
3. Implement the type definitions
4. Implement the `wizard.svelte.ts` store

After each phase, I'll review and we'll proceed to the next.
```

---

## 4. Phase 1: Foundation

### 4.1 Directory Creation

Create the following directory structure:

```bash
mkdir -p src/lib/workbench/components/NewProjectWizard/steps
mkdir -p src/lib/workbench/components/QuickCreate
mkdir -p src/lib/workbench/stores
mkdir -p src/lib/workbench/types
```

### 4.2 Type Definitions

#### `src/lib/workbench/types/wizard.ts`

```typescript
/**
 * VibeForge Wizard Type Definitions
 * 
 * Types for the modal wizard flow that guides users through project creation.
 */

import type { StackProfile } from '$lib/types/stacks';

// ============================================================================
// WIZARD STEP TYPES
// ============================================================================

export type WizardStep = 'intent' | 'languages' | 'stack' | 'config' | 'launch';

export const WIZARD_STEPS: WizardStep[] = ['intent', 'languages', 'stack', 'config', 'launch'];

export interface WizardStepMeta {
  title: string;
  description: string;
  teaches: string;  // What workbench feature this step introduces
}

export const WIZARD_STEP_META: Record<WizardStep, WizardStepMeta> = {
  intent: {
    title: 'Project Intent',
    description: "Define what you're building",
    teaches: 'Context Panel',
  },
  languages: {
    title: 'Languages',
    description: 'Choose your tech stack foundation',
    teaches: 'Language Contexts',
  },
  stack: {
    title: 'Stack',
    description: 'Select frameworks and tools',
    teaches: 'AI Recommendations',
  },
  config: {
    title: 'Configure',
    description: 'Fine-tune your setup',
    teaches: 'Settings Panel',
  },
  launch: {
    title: 'Launch',
    description: 'Create your project',
    teaches: 'Project Workspace',
  },
};

// ============================================================================
// PROJECT TYPES
// ============================================================================

export type ProjectType =
  | 'web-app'
  | 'api'
  | 'cli'
  | 'library'
  | 'desktop'
  | 'mobile'
  | 'fullstack'
  | 'data-pipeline'
  | 'ml-project';

export type Complexity = 'simple' | 'moderate' | 'complex' | 'enterprise';

export type Timeline = 'sprint' | 'month' | 'quarter' | 'year';

export interface FeatureSelection {
  authentication?: boolean;
  database?: boolean;
  api?: boolean;
  testing?: boolean;
  docker?: boolean;
  ci?: boolean;
  monitoring?: boolean;
  [key: string]: boolean | undefined;
}

// ============================================================================
// WIZARD DATA
// ============================================================================

export interface WizardData {
  // Step 1: Intent
  projectName: string;
  projectDescription: string;
  projectType: ProjectType;
  complexity: Complexity;

  // Step 2: Languages
  primaryLanguage: string | null;
  secondaryLanguages: string[];
  languagesConsidered: string[];  // For learning tracking

  // Step 3: Stack
  selectedStack: StackProfile | null;
  stacksCompared: string[];        // For learning tracking
  aiRecommendations: StackRecommendation[];

  // Step 4: Config
  features: FeatureSelection;
  teamSize: number;
  timeline: Timeline;

  // Step 5: Launch
  outputPath: string;
  generateReadme: boolean;
  initGit: boolean;
}

export interface StackRecommendation {
  stack: StackProfile;
  confidence: number;        // 0-1
  reasoning: string;
  matchScore: number;        // 0-100
  successRate: number;       // Historical success %
  source: 'ai' | 'empirical' | 'hybrid';
}

// ============================================================================
// VALIDATION
// ============================================================================

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

// ============================================================================
// WIZARD STATE
// ============================================================================

export interface WizardState {
  isOpen: boolean;
  currentStep: WizardStep;
  canProceed: boolean;
  isSubmitting: boolean;

  data: WizardData;
  validation: Record<WizardStep, ValidationResult>;

  // Learning integration
  sessionId: string | null;
  startedAt: Date | null;
}

// ============================================================================
// WIZARD OPTIONS
// ============================================================================

export interface WizardOpenOptions {
  skipToStep?: WizardStep;
  loadDraft?: boolean;
}

export interface WizardCloseOptions {
  saveDraft?: boolean;
}
```

#### `src/lib/workbench/types/project.ts`

```typescript
/**
 * VibeForge Project Type Definitions
 * 
 * Types for active project state and project management.
 */

import type { StackProfile } from '$lib/types/stacks';
import type { ProjectType, FeatureSelection, Complexity, Timeline } from './wizard';

// ============================================================================
// PROJECT
// ============================================================================

export interface Project {
  id: string;
  name: string;
  description: string;
  path: string;
  projectType: ProjectType;
  primaryLanguage: string;
  secondaryLanguages: string[];
  stack: StackProfile;
  features: FeatureSelection;
  createdAt: string;
  lastOpenedAt: string;
}

export interface ProjectConfig {
  id: string;
  name: string;
  description: string;
  path: string;
  projectType: ProjectType;
  primaryLanguage: string;
  secondaryLanguages: string[];
  stack: StackProfile;
  features: FeatureSelection;
  createdAt: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  path: string;
  lastOpened: string;
  stack: string;
  primaryLanguage: string;
}

// ============================================================================
// PROJECT CREATION
// ============================================================================

export interface ProjectGenerationConfig {
  name: string;
  description: string;
  projectType: ProjectType;
  primaryLanguage: string;
  secondaryLanguages: string[];
  stack: StackProfile | null;
  features: FeatureSelection;
  outputPath: string;
  generateReadme: boolean;
  initGit: boolean;
}

export interface ProjectGenerationResult {
  projectId: string;
  path: string;
  filesCreated: string[];
}

// ============================================================================
// PROJECT TRACKING (Learning Integration)
// ============================================================================

export interface ProjectCreationRecord {
  projectId: string;
  projectType: ProjectType;
  primaryLanguage: string;
  secondaryLanguages: string[];
  stackId: string;
  features: string[];
  complexity: Complexity;
  teamSize: number;
  timeline: Timeline;
  languagesConsidered: string[];
  stacksCompared: string[];
  usedAiRecommendation: boolean;
}
```

#### `src/lib/workbench/types/index.ts`

```typescript
/**
 * VibeForge Workbench Types - Barrel Export
 */

export * from './wizard';
export * from './project';
```

---

## 5. Phase 2: Modal Wizard Component

### 5.1 Wizard Store

#### `src/lib/workbench/stores/wizard.svelte.ts`

```typescript
/**
 * VibeForge Wizard Store
 * 
 * Manages the modal wizard state using Svelte 5 runes.
 * The wizard guides users through project creation while teaching workbench concepts.
 */

import { browser } from '$app/environment';
import type {
  WizardState,
  WizardStep,
  WizardData,
  ValidationResult,
  WizardOpenOptions,
  WizardCloseOptions,
  WIZARD_STEPS,
} from '../types/wizard';

// ============================================================================
// CONSTANTS
// ============================================================================

const STEP_ORDER: WizardStep[] = ['intent', 'languages', 'stack', 'config', 'launch'];
const STORAGE_KEY = 'vibeforge:wizard-draft';

// ============================================================================
// INITIAL STATE FACTORY
// ============================================================================

function createInitialData(): WizardData {
  return {
    projectName: '',
    projectDescription: '',
    projectType: 'web-app',
    complexity: 'moderate',
    primaryLanguage: null,
    secondaryLanguages: [],
    languagesConsidered: [],
    selectedStack: null,
    stacksCompared: [],
    aiRecommendations: [],
    features: {},
    teamSize: 1,
    timeline: 'month',
    outputPath: '',
    generateReadme: true,
    initGit: true,
  };
}

function createInitialValidation(): Record<WizardStep, ValidationResult> {
  return {
    intent: { isValid: false, errors: [], warnings: [] },
    languages: { isValid: false, errors: [], warnings: [] },
    stack: { isValid: false, errors: [], warnings: [] },
    config: { isValid: true, errors: [], warnings: [] },  // Optional step
    launch: { isValid: false, errors: [], warnings: [] },
  };
}

function createInitialState(): WizardState {
  return {
    isOpen: false,
    currentStep: 'intent',
    canProceed: false,
    isSubmitting: false,
    data: createInitialData(),
    validation: createInitialValidation(),
    sessionId: null,
    startedAt: null,
  };
}

// ============================================================================
// STATE
// ============================================================================

const state = $state<WizardState>(createInitialState());

// ============================================================================
// DERIVED STATE
// ============================================================================

const currentStepIndex = $derived(STEP_ORDER.indexOf(state.currentStep));
const isFirstStep = $derived(currentStepIndex === 0);
const isLastStep = $derived(currentStepIndex === STEP_ORDER.length - 1);
const progress = $derived(((currentStepIndex + 1) / STEP_ORDER.length) * 100);

const canGoBack = $derived(!isFirstStep && !state.isSubmitting);
const canGoForward = $derived(
  state.validation[state.currentStep].isValid && !state.isSubmitting
);

const currentStepValidation = $derived(state.validation[state.currentStep]);

const projectSummary = $derived({
  name: state.data.projectName,
  type: state.data.projectType,
  languages: [state.data.primaryLanguage, ...state.data.secondaryLanguages].filter(Boolean),
  stack: state.data.selectedStack?.name ?? 'None selected',
  features: Object.entries(state.data.features)
    .filter(([_, enabled]) => enabled)
    .map(([name]) => name),
  path: state.data.outputPath,
});

// ============================================================================
// PERSISTENCE
// ============================================================================

function saveDraft(): void {
  if (!browser) return;
  try {
    const draft = {
      data: state.data,
      currentStep: state.currentStep,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  } catch (e) {
    console.error('Failed to save wizard draft:', e);
  }
}

function loadDraft(): boolean {
  if (!browser) return false;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const draft = JSON.parse(stored);
      const savedAt = new Date(draft.savedAt);
      const hoursSince = (Date.now() - savedAt.getTime()) / (1000 * 60 * 60);
      
      // Only restore if less than 24 hours old
      if (hoursSince < 24) {
        state.data = { ...createInitialData(), ...draft.data };
        state.currentStep = draft.currentStep;
        validateCurrentStep();
        return true;
      }
    }
  } catch (e) {
    console.error('Failed to load wizard draft:', e);
  }
  return false;
}

function clearDraft(): void {
  if (!browser) return;
  localStorage.removeItem(STORAGE_KEY);
}

// ============================================================================
// VALIDATION
// ============================================================================

function validateStep(step: WizardStep, data: WizardData): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  switch (step) {
    case 'intent':
      if (!data.projectName.trim()) {
        errors.push('Project name is required');
      } else if (data.projectName.length < 2) {
        errors.push('Project name must be at least 2 characters');
      } else if (!/^[a-z0-9-_]+$/i.test(data.projectName)) {
        errors.push('Project name can only contain letters, numbers, hyphens, and underscores');
      }
      if (!data.projectDescription.trim()) {
        warnings.push('A description helps AI provide better recommendations');
      }
      break;

    case 'languages':
      if (!data.primaryLanguage) {
        errors.push('Select a primary language');
      }
      if (data.secondaryLanguages.length > 4) {
        warnings.push('More than 4 languages may increase project complexity');
      }
      break;

    case 'stack':
      if (!data.selectedStack) {
        errors.push('Select a technology stack');
      }
      break;

    case 'config':
      // Config step is optional, always valid
      break;

    case 'launch':
      if (!data.outputPath.trim()) {
        errors.push('Select an output directory');
      }
      break;
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

function validateCurrentStep(): void {
  const result = validateStep(state.currentStep, state.data);
  state.validation[state.currentStep] = result;
}

function validateAllSteps(): void {
  for (const step of STEP_ORDER) {
    state.validation[step] = validateStep(step, state.data);
  }
}

// ============================================================================
// ACTIONS
// ============================================================================

async function open(options?: WizardOpenOptions): Promise<void> {
  // Start learning session (non-blocking)
  try {
    const { vibeforgeClient } = await import('$lib/api/vibeforgeClient');
    const session = await vibeforgeClient.startProjectSession();
    state.sessionId = session.id;
  } catch (e) {
    console.warn('Learning session not started:', e);
  }

  state.startedAt = new Date();

  // Optionally load previous draft
  if (options?.loadDraft) {
    loadDraft();
  }

  // Optionally skip to step (for power users)
  if (options?.skipToStep) {
    state.currentStep = options.skipToStep;
  }

  validateCurrentStep();
  state.isOpen = true;
}

function close(options?: WizardCloseOptions): void {
  if (options?.saveDraft && state.data.projectName) {
    saveDraft();
  }
  state.isOpen = false;
}

function goToStep(step: WizardStep): void {
  const targetIndex = STEP_ORDER.indexOf(step);
  const currentIndex = STEP_ORDER.indexOf(state.currentStep);

  // Can always go back, but can only go forward if current is valid
  if (targetIndex < currentIndex || state.validation[state.currentStep].isValid) {
    state.currentStep = step;
    validateCurrentStep();
    saveDraft();
  }
}

function nextStep(): void {
  if (!canGoForward) return;

  const nextIndex = currentStepIndex + 1;
  if (nextIndex < STEP_ORDER.length) {
    trackStepCompletion(state.currentStep);
    state.currentStep = STEP_ORDER[nextIndex];
    validateCurrentStep();
    saveDraft();
  }
}

function previousStep(): void {
  if (!canGoBack) return;

  const prevIndex = currentStepIndex - 1;
  if (prevIndex >= 0) {
    state.currentStep = STEP_ORDER[prevIndex];
    validateCurrentStep();
  }
}

function updateData<K extends keyof WizardData>(key: K, value: WizardData[K]): void {
  state.data[key] = value;
  validateCurrentStep();
}

function setSubmitting(submitting: boolean): void {
  state.isSubmitting = submitting;
}

function reset(): void {
  Object.assign(state, createInitialState());
  clearDraft();
}

// ============================================================================
// LEARNING INTEGRATION
// ============================================================================

async function trackStepCompletion(step: WizardStep): Promise<void> {
  if (!state.sessionId) return;

  try {
    const { vibeforgeClient } = await import('$lib/api/vibeforgeClient');
    await vibeforgeClient.trackWizardStep({
      sessionId: state.sessionId,
      step,
      completedAt: new Date().toISOString(),
      data: getStepTrackingData(step),
    });
  } catch (e) {
    console.warn('Failed to track step completion:', e);
  }
}

function getStepTrackingData(step: WizardStep): Record<string, unknown> {
  switch (step) {
    case 'intent':
      return {
        projectType: state.data.projectType,
        complexity: state.data.complexity,
        descriptionLength: state.data.projectDescription.length,
      };
    case 'languages':
      return {
        primaryLanguage: state.data.primaryLanguage,
        secondaryCount: state.data.secondaryLanguages.length,
        languagesConsidered: state.data.languagesConsidered,
      };
    case 'stack':
      return {
        selectedStack: state.data.selectedStack?.id,
        stacksCompared: state.data.stacksCompared,
        usedAiRecommendation: state.data.aiRecommendations.some(
          (r) => r.stack.id === state.data.selectedStack?.id
        ),
      };
    default:
      return {};
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

export const wizardStore = {
  // State (readonly via getters)
  get isOpen() { return state.isOpen; },
  get currentStep() { return state.currentStep; },
  get isSubmitting() { return state.isSubmitting; },
  get data() { return state.data; },
  get validation() { return state.validation; },
  get sessionId() { return state.sessionId; },
  get startedAt() { return state.startedAt; },

  // Derived
  get currentStepIndex() { return currentStepIndex; },
  get isFirstStep() { return isFirstStep; },
  get isLastStep() { return isLastStep; },
  get progress() { return progress; },
  get canGoBack() { return canGoBack; },
  get canGoForward() { return canGoForward; },
  get currentStepValidation() { return currentStepValidation; },
  get projectSummary() { return projectSummary; },

  // Actions
  open,
  close,
  goToStep,
  nextStep,
  previousStep,
  updateData,
  setSubmitting,
  reset,
  validateCurrentStep,
  validateAllSteps,
  saveDraft,
  loadDraft,
  clearDraft,
};
```

### 5.2 Main Wizard Component

#### `src/lib/workbench/components/NewProjectWizard/NewProjectWizard.svelte`

```svelte
<!--
  NewProjectWizard.svelte
  
  Modal wizard for guided project creation.
  Overlays the workbench and teaches workbench concepts as users progress.
-->
<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { wizardStore } from '../../stores/wizard.svelte';
  import { projectStore } from '../../stores/project.svelte';
  import { WIZARD_STEP_META } from '../../types/wizard';
  import WizardProgress from './WizardProgress.svelte';
  import StepIntent from './steps/StepIntent.svelte';
  import StepLanguages from './steps/StepLanguages.svelte';
  import StepStack from './steps/StepStack.svelte';
  import StepConfig from './steps/StepConfig.svelte';
  import StepLaunch from './steps/StepLaunch.svelte';

  // Step components map
  const stepComponents = {
    intent: StepIntent,
    languages: StepLanguages,
    stack: StepStack,
    config: StepConfig,
    launch: StepLaunch,
  } as const;

  // Error state for launch
  let launchError = $state<string | null>(null);

  // Current step metadata
  const currentMeta = $derived(WIZARD_STEP_META[wizardStore.currentStep]);

  // Keyboard shortcuts
  function handleKeydown(e: KeyboardEvent): void {
    if (!wizardStore.isOpen) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      handleClose();
    } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (wizardStore.isLastStep) {
        handleLaunch();
      } else if (wizardStore.canGoForward) {
        wizardStore.nextStep();
      }
    }
  }

  function handleClose(): void {
    // Prompt to save draft if there's data
    if (wizardStore.data.projectName) {
      wizardStore.close({ saveDraft: true });
    } else {
      wizardStore.close();
    }
  }

  async function handleLaunch(): Promise<void> {
    if (!wizardStore.canGoForward || wizardStore.isSubmitting) return;

    launchError = null;
    wizardStore.setSubmitting(true);

    try {
      // Create project from wizard data
      await projectStore.createFromWizard(wizardStore.data);

      // Clear wizard state
      wizardStore.reset();

      // Modal closes automatically when isOpen becomes false
    } catch (e) {
      console.error('Failed to create project:', e);
      launchError = e instanceof Error ? e.message : 'Failed to create project';
      wizardStore.setSubmitting(false);
    }
  }

  function handleBackdropClick(e: MouseEvent): void {
    // Only close if clicking the backdrop itself, not the modal
    if (e.target === e.currentTarget) {
      handleClose();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if wizardStore.isOpen}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-40 bg-blacksteel-950/80 backdrop-blur-sm"
    transition:fade={{ duration: 200 }}
    on:click={handleBackdropClick}
    on:keydown={(e) => e.key === 'Escape' && handleClose()}
    role="button"
    tabindex="-1"
    aria-label="Close wizard"
  />

  <!-- Modal -->
  <div
    class="fixed inset-4 z-50 flex items-center justify-center pointer-events-none"
    role="dialog"
    aria-modal="true"
    aria-labelledby="wizard-title"
  >
    <div
      class="
        relative w-full max-w-3xl max-h-[90vh]
        bg-gunmetal-900 border border-gunmetal-700 rounded-xl
        shadow-2xl shadow-blacksteel-950/50
        pointer-events-auto
        flex flex-col
      "
      transition:fly={{ y: 20, duration: 300, easing: cubicOut }}
    >
      <!-- Header -->
      <header class="flex items-center justify-between px-6 py-4 border-b border-gunmetal-700">
        <div>
          <h2 id="wizard-title" class="text-lg font-semibold text-zinc-100">
            {currentMeta.title}
          </h2>
          <p class="text-sm text-zinc-400 mt-0.5">
            {currentMeta.description}
          </p>
        </div>

        <button
          type="button"
          class="p-2 text-zinc-400 hover:text-zinc-100 transition-colors rounded-lg hover:bg-gunmetal-800"
          aria-label="Close wizard"
          on:click={handleClose}
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      <!-- Progress -->
      <WizardProgress />

      <!-- Content -->
      <div class="flex-1 overflow-y-auto px-6 py-6">
        {#if launchError && wizardStore.isLastStep}
          <div class="mb-4 p-3 bg-red-900/20 border border-red-800 rounded-lg text-sm text-red-400">
            {launchError}
          </div>
        {/if}

        <svelte:component this={stepComponents[wizardStore.currentStep]} />
      </div>

      <!-- Footer -->
      <footer class="flex items-center justify-between px-6 py-4 border-t border-gunmetal-700 bg-gunmetal-900/50">
        <!-- Teaching hint -->
        <div class="text-xs text-zinc-500">
          <span class="text-ember-500">→</span>
          This sets up your <span class="text-zinc-400">{currentMeta.teaches}</span>
        </div>

        <!-- Navigation -->
        <div class="flex items-center gap-3">
          {#if !wizardStore.isFirstStep}
            <button
              type="button"
              class="px-4 py-2 text-sm text-zinc-300 hover:text-zinc-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!wizardStore.canGoBack}
              on:click={() => wizardStore.previousStep()}
            >
              Back
            </button>
          {/if}

          {#if wizardStore.isLastStep}
            <button
              type="button"
              class="
                px-5 py-2 text-sm font-medium rounded-lg
                bg-ember-600 text-white
                hover:bg-ember-500
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors
                flex items-center gap-2
              "
              disabled={!wizardStore.canGoForward || wizardStore.isSubmitting}
              on:click={handleLaunch}
            >
              {#if wizardStore.isSubmitting}
                <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Creating...
              {:else}
                Create Project
                <span class="text-xs opacity-75">⌘↵</span>
              {/if}
            </button>
          {:else}
            <button
              type="button"
              class="
                px-5 py-2 text-sm font-medium rounded-lg
                bg-gunmetal-700 text-zinc-100
                hover:bg-gunmetal-600
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors
              "
              disabled={!wizardStore.canGoForward}
              on:click={() => wizardStore.nextStep()}
            >
              Continue
              <span class="ml-1 text-xs opacity-75">⌘↵</span>
            </button>
          {/if}
        </div>
      </footer>
    </div>
  </div>
{/if}
```

### 5.3 Wizard Progress Component

#### `src/lib/workbench/components/NewProjectWizard/WizardProgress.svelte`

```svelte
<!--
  WizardProgress.svelte
  
  Step indicator for the wizard showing progress and allowing navigation.
-->
<script lang="ts">
  import { wizardStore } from '../../stores/wizard.svelte';
  import { WIZARD_STEP_META, type WizardStep } from '../../types/wizard';

  const steps: WizardStep[] = ['intent', 'languages', 'stack', 'config', 'launch'];

  function getStepStatus(step: WizardStep, index: number): 'completed' | 'current' | 'upcoming' {
    const currentIndex = wizardStore.currentStepIndex;
    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'current';
    return 'upcoming';
  }

  function canNavigateToStep(step: WizardStep, index: number): boolean {
    const currentIndex = wizardStore.currentStepIndex;
    // Can always go back, can only go forward if current is valid
    return index < currentIndex || (index === currentIndex + 1 && wizardStore.canGoForward);
  }

  function handleStepClick(step: WizardStep, index: number): void {
    if (index < wizardStore.currentStepIndex) {
      wizardStore.goToStep(step);
    }
  }
</script>

<div class="px-6 py-3 border-b border-gunmetal-800 bg-gunmetal-900/30">
  <div class="flex items-center justify-between">
    {#each steps as step, index}
      {@const status = getStepStatus(step, index)}
      {@const meta = WIZARD_STEP_META[step]}
      {@const isClickable = index < wizardStore.currentStepIndex}
      
      <!-- Step indicator -->
      <button
        type="button"
        class="
          flex items-center gap-2 group
          {isClickable ? 'cursor-pointer' : 'cursor-default'}
        "
        disabled={!isClickable}
        on:click={() => handleStepClick(step, index)}
      >
        <!-- Circle -->
        <div
          class="
            w-8 h-8 rounded-full flex items-center justify-center
            text-sm font-medium transition-all
            {status === 'completed' 
              ? 'bg-ember-600 text-white' 
              : status === 'current'
                ? 'bg-ember-600/20 text-ember-400 ring-2 ring-ember-500'
                : 'bg-gunmetal-800 text-zinc-500'}
            {isClickable ? 'group-hover:ring-2 group-hover:ring-ember-500/50' : ''}
          "
        >
          {#if status === 'completed'}
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          {:else}
            {index + 1}
          {/if}
        </div>

        <!-- Label (hidden on mobile) -->
        <span
          class="
            hidden sm:block text-sm transition-colors
            {status === 'current' 
              ? 'text-zinc-100 font-medium' 
              : status === 'completed'
                ? 'text-zinc-400'
                : 'text-zinc-600'}
            {isClickable ? 'group-hover:text-zinc-300' : ''}
          "
        >
          {meta.title}
        </span>
      </button>

      <!-- Connector line -->
      {#if index < steps.length - 1}
        <div
          class="
            flex-1 h-0.5 mx-2
            {index < wizardStore.currentStepIndex 
              ? 'bg-ember-600' 
              : 'bg-gunmetal-700'}
          "
        />
      {/if}
    {/each}
  </div>
</div>
```

### 5.4 Step Components (Migrate from existing)

Note: Migrate the existing step components from `/routes/wizard/` and adapt them to use the new `wizardStore`. Below is an example for StepIntent:

#### `src/lib/workbench/components/NewProjectWizard/steps/StepIntent.svelte`

```svelte
<!--
  StepIntent.svelte
  
  Step 1: Define project intent (name, description, type, complexity)
-->
<script lang="ts">
  import { wizardStore } from '../../../stores/wizard.svelte';
  import type { ProjectType, Complexity } from '../../../types/wizard';

  const projectTypes: { value: ProjectType; label: string; icon: string }[] = [
    { value: 'web-app', label: 'Web Application', icon: '🌐' },
    { value: 'api', label: 'API / Backend', icon: '⚡' },
    { value: 'fullstack', label: 'Full Stack', icon: '🏗️' },
    { value: 'cli', label: 'CLI Tool', icon: '💻' },
    { value: 'library', label: 'Library / Package', icon: '📦' },
    { value: 'desktop', label: 'Desktop App', icon: '🖥️' },
    { value: 'mobile', label: 'Mobile App', icon: '📱' },
    { value: 'data-pipeline', label: 'Data Pipeline', icon: '🔄' },
    { value: 'ml-project', label: 'ML / AI Project', icon: '🤖' },
  ];

  const complexityLevels: { value: Complexity; label: string; description: string }[] = [
    { value: 'simple', label: 'Simple', description: 'Quick prototype or small tool' },
    { value: 'moderate', label: 'Moderate', description: 'Standard project with typical features' },
    { value: 'complex', label: 'Complex', description: 'Large project with many integrations' },
    { value: 'enterprise', label: 'Enterprise', description: 'Mission-critical with strict requirements' },
  ];

  // Reactive bindings to wizard store
  let projectName = $state(wizardStore.data.projectName);
  let projectDescription = $state(wizardStore.data.projectDescription);
  let projectType = $state(wizardStore.data.projectType);
  let complexity = $state(wizardStore.data.complexity);

  // Sync to store on change
  $effect(() => {
    wizardStore.updateData('projectName', projectName);
  });

  $effect(() => {
    wizardStore.updateData('projectDescription', projectDescription);
  });

  $effect(() => {
    wizardStore.updateData('projectType', projectType);
  });

  $effect(() => {
    wizardStore.updateData('complexity', complexity);
  });

  const validation = $derived(wizardStore.validation.intent);
</script>

<div class="space-y-6">
  <!-- Project Name -->
  <div>
    <label for="project-name" class="block text-sm font-medium text-zinc-300 mb-2">
      Project Name <span class="text-red-400">*</span>
    </label>
    <input
      id="project-name"
      type="text"
      bind:value={projectName}
      placeholder="my-awesome-project"
      class="
        w-full px-4 py-3
        bg-gunmetal-800 border rounded-lg
        text-zinc-100 placeholder:text-zinc-600
        focus:outline-none focus:ring-2 focus:ring-ember-500/50
        transition-all
        {validation.errors.some(e => e.includes('name')) 
          ? 'border-red-500' 
          : 'border-gunmetal-700 focus:border-ember-500'}
      "
      autofocus
    />
    {#if validation.errors.some(e => e.includes('name'))}
      <p class="mt-1 text-sm text-red-400">
        {validation.errors.find(e => e.includes('name'))}
      </p>
    {/if}
  </div>

  <!-- Project Description -->
  <div>
    <label for="project-description" class="block text-sm font-medium text-zinc-300 mb-2">
      Description
      <span class="text-zinc-500 font-normal">(helps AI recommendations)</span>
    </label>
    <textarea
      id="project-description"
      bind:value={projectDescription}
      placeholder="Describe what you're building and its main purpose..."
      rows="3"
      class="
        w-full px-4 py-3
        bg-gunmetal-800 border border-gunmetal-700 rounded-lg
        text-zinc-100 placeholder:text-zinc-600
        focus:outline-none focus:border-ember-500 focus:ring-2 focus:ring-ember-500/50
        transition-all resize-none
      "
    />
    {#if validation.warnings.some(w => w.includes('description'))}
      <p class="mt-1 text-sm text-amber-400">
        💡 {validation.warnings.find(w => w.includes('description'))}
      </p>
    {/if}
  </div>

  <!-- Project Type -->
  <div>
    <label class="block text-sm font-medium text-zinc-300 mb-3">
      Project Type <span class="text-red-400">*</span>
    </label>
    <div class="grid grid-cols-3 gap-2">
      {#each projectTypes as type}
        <button
          type="button"
          class="
            flex items-center gap-2 px-3 py-2.5
            rounded-lg border text-left transition-all
            {projectType === type.value
              ? 'bg-ember-600/20 border-ember-500 text-ember-400'
              : 'bg-gunmetal-800 border-gunmetal-700 text-zinc-400 hover:border-gunmetal-600 hover:text-zinc-300'}
          "
          on:click={() => projectType = type.value}
        >
          <span class="text-lg">{type.icon}</span>
          <span class="text-sm">{type.label}</span>
        </button>
      {/each}
    </div>
  </div>

  <!-- Complexity -->
  <div>
    <label class="block text-sm font-medium text-zinc-300 mb-3">
      Complexity
    </label>
    <div class="grid grid-cols-2 gap-2">
      {#each complexityLevels as level}
        <button
          type="button"
          class="
            flex flex-col px-4 py-3
            rounded-lg border text-left transition-all
            {complexity === level.value
              ? 'bg-ember-600/20 border-ember-500'
              : 'bg-gunmetal-800 border-gunmetal-700 hover:border-gunmetal-600'}
          "
          on:click={() => complexity = level.value}
        >
          <span
            class="text-sm font-medium {complexity === level.value ? 'text-ember-400' : 'text-zinc-300'}"
          >
            {level.label}
          </span>
          <span class="text-xs text-zinc-500 mt-0.5">{level.description}</span>
        </button>
      {/each}
    </div>
  </div>
</div>
```

---

## 6. Phase 3: Data Handoff

### 6.1 Project Store

#### `src/lib/workbench/stores/project.svelte.ts`

```typescript
/**
 * VibeForge Project Store
 * 
 * Manages the active project state and handles wizard-to-workbench handoff.
 */

import { browser } from '$app/environment';
import type { WizardData } from '../types/wizard';
import type { 
  Project, 
  ProjectSummary, 
  ProjectGenerationResult,
  ProjectCreationRecord 
} from '../types/project';
import type { ContextBlock } from '$lib/core/types';

// ============================================================================
// CONSTANTS
// ============================================================================

const RECENT_KEY = 'vibeforge:recent-projects';
const MAX_RECENT = 10;

// ============================================================================
// STATE
// ============================================================================

interface ProjectState {
  current: Project | null;
  isLoading: boolean;
  error: string | null;
  recentProjects: ProjectSummary[];
}

function loadRecentProjects(): ProjectSummary[] {
  if (!browser) return [];
  try {
    const stored = localStorage.getItem(RECENT_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

const state = $state<ProjectState>({
  current: null,
  isLoading: false,
  error: null,
  recentProjects: loadRecentProjects(),
});

// ============================================================================
// DERIVED
// ============================================================================

const hasActiveProject = $derived(state.current !== null);
const projectName = $derived(state.current?.name ?? '');
const projectPath = $derived(state.current?.path ?? '');
const projectStack = $derived(state.current?.stack.name ?? '');

// ============================================================================
// PERSISTENCE
// ============================================================================

function saveRecentProject(project: ProjectSummary): void {
  if (!browser) return;

  // Remove if already exists, add to front
  const filtered = state.recentProjects.filter((p) => p.id !== project.id);
  const updated = [project, ...filtered].slice(0, MAX_RECENT);

  state.recentProjects = updated;
  localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
}

function removeRecentProject(projectId: string): void {
  if (!browser) return;

  state.recentProjects = state.recentProjects.filter((p) => p.id !== projectId);
  localStorage.setItem(RECENT_KEY, JSON.stringify(state.recentProjects));
}

// ============================================================================
// WIZARD HANDOFF - THE CRITICAL FUNCTION
// ============================================================================

async function createFromWizard(wizardData: WizardData): Promise<Project> {
  state.isLoading = true;
  state.error = null;

  try {
    // 1. Generate project files via Tauri backend
    const { invoke } = await import('@tauri-apps/api/core');
    const generationResult = await invoke<ProjectGenerationResult>('generate_project', {
      config: {
        name: wizardData.projectName,
        description: wizardData.projectDescription,
        projectType: wizardData.projectType,
        primaryLanguage: wizardData.primaryLanguage,
        secondaryLanguages: wizardData.secondaryLanguages,
        stack: wizardData.selectedStack,
        features: wizardData.features,
        outputPath: wizardData.outputPath,
        generateReadme: wizardData.generateReadme,
        initGit: wizardData.initGit,
      },
    });

    // 2. Create project object
    const project: Project = {
      id: generationResult.projectId,
      name: wizardData.projectName,
      description: wizardData.projectDescription,
      path: generationResult.path,
      projectType: wizardData.projectType,
      primaryLanguage: wizardData.primaryLanguage!,
      secondaryLanguages: wizardData.secondaryLanguages,
      stack: wizardData.selectedStack!,
      features: wizardData.features,
      createdAt: new Date().toISOString(),
      lastOpenedAt: new Date().toISOString(),
    };

    // 3. Initialize workbench state from project
    await initializeWorkbenchFromProject(project, wizardData);

    // 4. Track project creation for learning (non-blocking)
    trackProjectCreation(project, wizardData).catch(console.warn);

    // 5. Save to recent projects
    saveRecentProject({
      id: project.id,
      name: project.name,
      path: project.path,
      lastOpened: project.lastOpenedAt,
      stack: project.stack.name,
      primaryLanguage: project.primaryLanguage,
    });

    // 6. Set as current project
    state.current = project;
    state.isLoading = false;

    return project;
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to create project';
    state.error = message;
    state.isLoading = false;
    throw new Error(message);
  }
}

// ============================================================================
// WORKBENCH INITIALIZATION
// ============================================================================

async function initializeWorkbenchFromProject(
  project: Project,
  wizardData: WizardData
): Promise<void> {
  // Import stores dynamically to avoid circular dependencies
  const { workspaceStore } = await import('$lib/core/stores/workspace.svelte');
  const { contextBlocksStore } = await import('$lib/core/stores/contextBlocks.svelte');
  const { promptStore } = await import('$lib/core/stores/prompt.svelte');

  // 1. Set up workspace
  workspaceStore.setWorkspace({
    id: project.id,
    name: project.name,
    settings: {
      theme: 'dark',
      autoSave: true,
      fontSize: 14,
    },
    createdAt: project.createdAt,
    updatedAt: project.createdAt,
  });

  // 2. Create initial context blocks from project data
  const contextBlocks = generateInitialContextBlocks(project, wizardData);
  contextBlocksStore.setBlocks(contextBlocks);

  // 3. Set up initial prompt template
  const initialPrompt = generateInitialPrompt(project);
  promptStore.setText(initialPrompt);

  // 4. Load language-specific patterns (optional, non-blocking)
  loadLanguagePatterns(project.primaryLanguage).catch(console.warn);
}

function generateInitialContextBlocks(
  project: Project,
  wizardData: WizardData
): ContextBlock[] {
  const blocks: ContextBlock[] = [];

  // System context with project info
  blocks.push({
    id: 'ctx-project-system',
    kind: 'system',
    name: 'Project Context',
    content: `You are assisting with ${project.name}, a ${project.projectType} project.

## Project Overview
${project.description || 'No description provided.'}

## Tech Stack
- Primary Language: ${project.primaryLanguage}
${project.secondaryLanguages.length > 0 ? `- Secondary Languages: ${project.secondaryLanguages.join(', ')}` : ''}
- Stack: ${project.stack.name}
${project.stack.framework ? `- Framework: ${project.stack.framework}` : ''}

## Guidelines
- Follow ${project.primaryLanguage} best practices
- Use consistent code style
- Write clear, documented code`,
    isActive: true,
    metadata: { autoGenerated: true, source: 'wizard' },
  });

  // Stack-specific context
  if (project.stack.description) {
    blocks.push({
      id: 'ctx-stack-info',
      kind: 'knowledge',
      name: `${project.stack.name} Stack`,
      content: project.stack.description,
      isActive: true,
      metadata: { autoGenerated: true, source: 'stack-profile' },
    });
  }

  // Feature-specific contexts (inactive by default)
  const enabledFeatures = Object.entries(wizardData.features)
    .filter(([_, enabled]) => enabled)
    .map(([name]) => name);

  if (enabledFeatures.includes('authentication')) {
    blocks.push({
      id: 'ctx-feature-auth',
      kind: 'knowledge',
      name: 'Authentication Guidelines',
      content: `## Authentication Implementation
- Use secure password hashing (bcrypt/argon2)
- Implement JWT or session-based auth
- Follow OWASP authentication guidelines
- Never store plain text passwords
- Implement proper session management`,
      isActive: false,
      metadata: { autoGenerated: true, source: 'feature-auth' },
    });
  }

  if (enabledFeatures.includes('database')) {
    blocks.push({
      id: 'ctx-feature-db',
      kind: 'knowledge',
      name: 'Database Guidelines',
      content: `## Database Best Practices
- Use parameterized queries (prevent SQL injection)
- Implement proper migrations
- Add appropriate indexes
- Use connection pooling
- Handle transactions properly`,
      isActive: false,
      metadata: { autoGenerated: true, source: 'feature-db' },
    });
  }

  if (enabledFeatures.includes('testing')) {
    blocks.push({
      id: 'ctx-feature-testing',
      kind: 'knowledge',
      name: 'Testing Guidelines',
      content: `## Testing Best Practices
- Write unit tests for business logic
- Use integration tests for API endpoints
- Maintain high code coverage (80%+)
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)`,
      isActive: false,
      metadata: { autoGenerated: true, source: 'feature-testing' },
    });
  }

  return blocks;
}

function generateInitialPrompt(project: Project): string {
  return `# Working on: ${project.name}

Describe what you'd like to build or the problem you're solving:

`;
}

async function loadLanguagePatterns(language: string): Promise<void> {
  try {
    const { vibeforgeClient } = await import('$lib/api/vibeforgeClient');
    const { contextBlocksStore } = await import('$lib/core/stores/contextBlocks.svelte');

    const patterns = await vibeforgeClient.getLanguagePatterns(language);

    patterns.forEach((pattern) => {
      contextBlocksStore.addBlock({
        id: `pattern-${pattern.id}`,
        kind: 'pattern',
        name: pattern.name,
        content: pattern.template,
        isActive: false,
        metadata: { source: 'language-patterns', language },
      });
    });
  } catch (e) {
    // Patterns are optional
    console.debug('Language patterns not available:', e);
  }
}

// ============================================================================
// LEARNING INTEGRATION
// ============================================================================

async function trackProjectCreation(
  project: Project,
  wizardData: WizardData
): Promise<void> {
  try {
    const { vibeforgeClient } = await import('$lib/api/vibeforgeClient');

    const record: ProjectCreationRecord = {
      projectId: project.id,
      projectType: project.projectType,
      primaryLanguage: project.primaryLanguage,
      secondaryLanguages: project.secondaryLanguages,
      stackId: project.stack.id,
      features: Object.keys(wizardData.features).filter((k) => wizardData.features[k]),
      complexity: wizardData.complexity,
      teamSize: wizardData.teamSize,
      timeline: wizardData.timeline,
      languagesConsidered: wizardData.languagesConsidered,
      stacksCompared: wizardData.stacksCompared,
      usedAiRecommendation: wizardData.aiRecommendations.some(
        (r) => r.stack.id === project.stack.id
      ),
    };

    await vibeforgeClient.recordProjectCreation(record);
  } catch (e) {
    // Non-blocking - learning is optional
    console.warn('Failed to track project creation:', e);
  }
}

// ============================================================================
// PROJECT OPERATIONS
// ============================================================================

async function openProject(projectPath: string): Promise<Project> {
  state.isLoading = true;
  state.error = null;

  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const config = await invoke<Project>('load_project_config', { path: projectPath });

    const project: Project = {
      ...config,
      lastOpenedAt: new Date().toISOString(),
    };

    // Initialize workbench with minimal wizard data
    await initializeWorkbenchFromProject(project, {
      projectName: project.name,
      projectDescription: project.description,
      projectType: project.projectType,
      complexity: 'moderate',
      primaryLanguage: project.primaryLanguage,
      secondaryLanguages: project.secondaryLanguages,
      languagesConsidered: [],
      selectedStack: project.stack,
      stacksCompared: [],
      aiRecommendations: [],
      features: project.features,
      teamSize: 1,
      timeline: 'month',
      outputPath: project.path,
      generateReadme: false,
      initGit: false,
    });

    saveRecentProject({
      id: project.id,
      name: project.name,
      path: project.path,
      lastOpened: project.lastOpenedAt,
      stack: project.stack.name,
      primaryLanguage: project.primaryLanguage,
    });

    state.current = project;
    state.isLoading = false;

    return project;
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to open project';
    state.error = message;
    state.isLoading = false;
    throw new Error(message);
  }
}

async function closeProject(): Promise<void> {
  const { workspaceStore } = await import('$lib/core/stores/workspace.svelte');
  const { contextBlocksStore } = await import('$lib/core/stores/contextBlocks.svelte');
  const { promptStore } = await import('$lib/core/stores/prompt.svelte');

  state.current = null;

  // Clear workbench state
  contextBlocksStore.setBlocks([]);
  promptStore.clearText();
  workspaceStore.clearWorkspace();
}

function clearError(): void {
  state.error = null;
}

// ============================================================================
// EXPORTS
// ============================================================================

export const projectStore = {
  // State
  get current() { return state.current; },
  get isLoading() { return state.isLoading; },
  get error() { return state.error; },
  get recentProjects() { return state.recentProjects; },

  // Derived
  get hasActiveProject() { return hasActiveProject; },
  get projectName() { return projectName; },
  get projectPath() { return projectPath; },
  get projectStack() { return projectStack; },

  // Actions
  createFromWizard,
  openProject,
  closeProject,
  clearError,
  removeRecentProject,
};
```

---

## 7. Phase 4: Power User Flow

### 7.1 Quick Create Dialog

#### `src/lib/workbench/components/QuickCreate/QuickCreateDialog.svelte`

```svelte
<!--
  QuickCreateDialog.svelte
  
  Minimal project creation for power users who want to skip the full wizard.
-->
<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { projectStore } from '../../stores/project.svelte';
  import { wizardStore } from '../../stores/wizard.svelte';

  // Props
  interface Props {
    isOpen: boolean;
    onClose: () => void;
  }

  let { isOpen, onClose }: Props = $props();

  // Form state
  let projectName = $state('');
  let selectedLanguage = $state<string | null>(null);
  let outputPath = $state('');
  let isSubmitting = $state(false);
  let error = $state<string | null>(null);

  // Quick access languages
  const quickLanguages = [
    { id: 'typescript', name: 'TypeScript', icon: '🔷' },
    { id: 'python', name: 'Python', icon: '🐍' },
    { id: 'rust', name: 'Rust', icon: '🦀' },
    { id: 'go', name: 'Go', icon: '🔵' },
    { id: 'javascript', name: 'JavaScript', icon: '🟨' },
    { id: 'java', name: 'Java', icon: '☕' },
  ];

  // Validation
  const isValid = $derived(
    projectName.trim().length >= 2 &&
    /^[a-z0-9-_]+$/i.test(projectName) &&
    selectedLanguage !== null &&
    outputPath.trim().length > 0
  );

  // Reset form when dialog opens
  $effect(() => {
    if (isOpen) {
      projectName = '';
      selectedLanguage = null;
      outputPath = '';
      error = null;
    }
  });

  async function handleCreate(): Promise<void> {
    if (!isValid || isSubmitting) return;

    isSubmitting = true;
    error = null;

    try {
      // Create with minimal defaults
      await projectStore.createFromWizard({
        projectName,
        projectDescription: '',
        projectType: 'web-app',
        complexity: 'moderate',
        primaryLanguage: selectedLanguage,
        secondaryLanguages: [],
        languagesConsidered: [selectedLanguage!],
        selectedStack: null,  // Will use default for language
        stacksCompared: [],
        aiRecommendations: [],
        features: {},
        teamSize: 1,
        timeline: 'month',
        outputPath,
        generateReadme: true,
        initGit: true,
      });

      onClose();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create project';
    } finally {
      isSubmitting = false;
    }
  }

  async function selectDirectory(): Promise<void> {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const selected = await open({
        directory: true,
        multiple: false,
        title: 'Select Project Location',
      });

      if (selected) {
        outputPath = selected as string;
      }
    } catch (e) {
      console.error('Failed to open directory picker:', e);
    }
  }

  function switchToWizard(): void {
    onClose();
    wizardStore.open();
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (!isOpen) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && isValid) {
      e.preventDefault();
      handleCreate();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-50 bg-blacksteel-950/80 backdrop-blur-sm"
    transition:fade={{ duration: 150 }}
    on:click={onClose}
    on:keydown={(e) => e.key === 'Escape' && onClose()}
    role="button"
    tabindex="-1"
    aria-label="Close dialog"
  />

  <!-- Dialog -->
  <div
    class="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] pointer-events-none"
    role="dialog"
    aria-modal="true"
    aria-labelledby="quick-create-title"
  >
    <div
      class="
        w-full max-w-md
        bg-gunmetal-900 border border-gunmetal-700 rounded-xl
        shadow-2xl shadow-blacksteel-950/50
        pointer-events-auto
      "
      transition:fly={{ y: -10, duration: 200 }}
    >
      <!-- Header -->
      <div class="px-5 py-4 border-b border-gunmetal-800">
        <h2 id="quick-create-title" class="text-base font-medium text-zinc-100">
          Quick Create
        </h2>
        <p class="text-xs text-zinc-500 mt-1">
          Skip the wizard with sensible defaults
        </p>
      </div>

      <!-- Form -->
      <div class="p-5 space-y-5">
        <!-- Project Name -->
        <div>
          <label for="project-name" class="block text-sm text-zinc-400 mb-1.5">
            Project Name
          </label>
          <input
            id="project-name"
            type="text"
            bind:value={projectName}
            placeholder="my-awesome-project"
            class="
              w-full px-3 py-2.5
              bg-gunmetal-800 border border-gunmetal-700 rounded-lg
              text-zinc-100 placeholder:text-zinc-600
              focus:outline-none focus:border-ember-500 focus:ring-2 focus:ring-ember-500/50
              transition-all
            "
            autofocus
          />
        </div>

        <!-- Language -->
        <div>
          <label class="block text-sm text-zinc-400 mb-2">
            Primary Language
          </label>
          <div class="grid grid-cols-3 gap-2">
            {#each quickLanguages as lang}
              <button
                type="button"
                class="
                  flex flex-col items-center gap-1.5 py-3
                  rounded-lg border transition-all
                  {selectedLanguage === lang.id
                    ? 'bg-ember-600/20 border-ember-500 text-ember-400'
                    : 'bg-gunmetal-800 border-gunmetal-700 text-zinc-400 hover:border-gunmetal-600 hover:text-zinc-300'}
                "
                on:click={() => (selectedLanguage = lang.id)}
              >
                <span class="text-xl">{lang.icon}</span>
                <span class="text-xs">{lang.name}</span>
              </button>
            {/each}
          </div>
        </div>

        <!-- Output Path -->
        <div>
          <label for="output-path" class="block text-sm text-zinc-400 mb-1.5">
            Location
          </label>
          <div class="flex gap-2">
            <input
              id="output-path"
              type="text"
              bind:value={outputPath}
              placeholder="Select a directory..."
              class="
                flex-1 px-3 py-2.5
                bg-gunmetal-800 border border-gunmetal-700 rounded-lg
                text-zinc-100 placeholder:text-zinc-600
                focus:outline-none focus:border-ember-500 focus:ring-2 focus:ring-ember-500/50
                transition-all
              "
              readonly
            />
            <button
              type="button"
              class="
                px-4 py-2.5
                bg-gunmetal-700 border border-gunmetal-600 rounded-lg
                text-zinc-300 hover:bg-gunmetal-600 hover:text-zinc-100
                transition-colors
              "
              on:click={selectDirectory}
            >
              Browse
            </button>
          </div>
        </div>

        <!-- Error -->
        {#if error}
          <div class="p-3 bg-red-900/20 border border-red-800 rounded-lg text-sm text-red-400">
            {error}
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between px-5 py-4 border-t border-gunmetal-800 bg-gunmetal-900/50">
        <button
          type="button"
          class="text-sm text-zinc-500 hover:text-zinc-400 transition-colors"
          on:click={switchToWizard}
        >
          Use Full Wizard →
        </button>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-300 transition-colors"
            on:click={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            class="
              px-5 py-2 text-sm font-medium rounded-lg
              bg-ember-600 text-white
              hover:bg-ember-500
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
              flex items-center gap-2
            "
            disabled={!isValid || isSubmitting}
            on:click={handleCreate}
          >
            {#if isSubmitting}
              <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            {/if}
            Create
            <span class="text-xs opacity-75">⌘↵</span>
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
```

### 7.2 User Preferences Store

#### `src/lib/workbench/stores/userPreferences.svelte.ts`

```typescript
/**
 * VibeForge User Preferences Store
 * 
 * Manages user preferences for power user features.
 */

import { browser } from '$app/environment';

// ============================================================================
// TYPES
// ============================================================================

interface UserPreferences {
  // Wizard behavior
  skipWizard: boolean;
  showWizardOnFirstVisit: boolean;
  rememberLastStack: boolean;

  // Workbench behavior
  autoSavePrompts: boolean;
  confirmBeforeClose: boolean;

  // UI preferences
  sidebarWidth: number;
  outputPanelWidth: number;
  fontSize: number;

  // Keyboard shortcuts (customizable)
  shortcuts: Record<string, string>;
}

// ============================================================================
// DEFAULTS
// ============================================================================

const STORAGE_KEY = 'vibeforge:user-preferences';

const defaultPreferences: UserPreferences = {
  skipWizard: false,
  showWizardOnFirstVisit: true,
  rememberLastStack: true,
  autoSavePrompts: true,
  confirmBeforeClose: true,
  sidebarWidth: 288,
  outputPanelWidth: 384,
  fontSize: 14,
  shortcuts: {
    newProject: 'mod+n',
    openProject: 'mod+o',
    commandPalette: 'mod+k',
    runPrompt: 'mod+enter',
    savePrompt: 'mod+s',
    closeProject: 'mod+w',
  },
};

// ============================================================================
// PERSISTENCE
// ============================================================================

function loadPreferences(): UserPreferences {
  if (!browser) return defaultPreferences;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? { ...defaultPreferences, ...JSON.parse(stored) } : defaultPreferences;
  } catch {
    return defaultPreferences;
  }
}

function savePreferences(prefs: UserPreferences): void {
  if (!browser) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

// ============================================================================
// STATE
// ============================================================================

const state = $state<UserPreferences>(loadPreferences());

// ============================================================================
// ACTIONS
// ============================================================================

function update<K extends keyof UserPreferences>(key: K, value: UserPreferences[K]): void {
  state[key] = value;
  savePreferences(state);
}

function updateShortcut(action: string, shortcut: string): void {
  state.shortcuts[action] = shortcut;
  savePreferences(state);
}

function reset(): void {
  Object.assign(state, defaultPreferences);
  savePreferences(state);
}

function resetShortcuts(): void {
  state.shortcuts = { ...defaultPreferences.shortcuts };
  savePreferences(state);
}

// ============================================================================
// EXPORTS
// ============================================================================

export const userPreferencesStore = {
  // Wizard preferences
  get skipWizard() { return state.skipWizard; },
  get showWizardOnFirstVisit() { return state.showWizardOnFirstVisit; },
  get rememberLastStack() { return state.rememberLastStack; },

  // Workbench preferences
  get autoSavePrompts() { return state.autoSavePrompts; },
  get confirmBeforeClose() { return state.confirmBeforeClose; },

  // UI preferences
  get sidebarWidth() { return state.sidebarWidth; },
  get outputPanelWidth() { return state.outputPanelWidth; },
  get fontSize() { return state.fontSize; },

  // Shortcuts
  get shortcuts() { return state.shortcuts; },

  // All preferences (for settings UI)
  get all() { return state; },

  // Actions
  update,
  updateShortcut,
  reset,
  resetShortcuts,
};
```

---

## 8. Type Definitions

All type definitions are provided in Phase 1 (Section 4.2). The key files are:

- `src/lib/workbench/types/wizard.ts` - Wizard types
- `src/lib/workbench/types/project.ts` - Project types
- `src/lib/workbench/types/index.ts` - Barrel export

---

## 9. Store Implementations

All store implementations are provided in:

- Phase 2 (Section 5.1): `wizard.svelte.ts`
- Phase 3 (Section 6.1): `project.svelte.ts`
- Phase 4 (Section 7.2): `userPreferences.svelte.ts`

---

## 10. Component Specifications

### Component Hierarchy

```
WorkbenchShell.svelte
├── TopBar.svelte
├── ContextPanel.svelte
├── PromptEditor.svelte
├── OutputPanel.svelte
├── StatusBar.svelte
├── WelcomeOverlay.svelte (conditional)
├── NewProjectWizard.svelte (modal)
│   ├── WizardProgress.svelte
│   └── steps/
│       ├── StepIntent.svelte
│       ├── StepLanguages.svelte
│       ├── StepStack.svelte
│       ├── StepConfig.svelte
│       └── StepLaunch.svelte
├── QuickCreateDialog.svelte (modal)
└── CommandPalette.svelte (modal)
```

### Key Component Props

| Component | Props | Description |
|-----------|-------|-------------|
| NewProjectWizard | (none - uses store) | Self-contained modal |
| QuickCreateDialog | `isOpen`, `onClose` | Controlled modal |
| WelcomeOverlay | `onNewProject`, `onQuickCreate`, `onOpenProject` | First-visit experience |
| CommandPalette | `isOpen`, `onClose`, `onSelect` | Command interface |

---

## 11. Testing Strategy

### Unit Tests

```typescript
// src/lib/workbench/stores/__tests__/wizard.test.ts

import { describe, it, expect, beforeEach } from 'vitest';
import { wizardStore } from '../wizard.svelte';

describe('wizardStore', () => {
  beforeEach(() => {
    wizardStore.reset();
  });

  describe('navigation', () => {
    it('should start at intent step', () => {
      expect(wizardStore.currentStep).toBe('intent');
    });

    it('should not go forward without valid data', () => {
      wizardStore.nextStep();
      expect(wizardStore.currentStep).toBe('intent');
    });

    it('should go forward with valid data', () => {
      wizardStore.updateData('projectName', 'test-project');
      wizardStore.nextStep();
      expect(wizardStore.currentStep).toBe('languages');
    });

    it('should allow going back', () => {
      wizardStore.updateData('projectName', 'test-project');
      wizardStore.nextStep();
      wizardStore.previousStep();
      expect(wizardStore.currentStep).toBe('intent');
    });
  });

  describe('validation', () => {
    it('should validate project name', () => {
      wizardStore.updateData('projectName', '');
      expect(wizardStore.validation.intent.isValid).toBe(false);

      wizardStore.updateData('projectName', 'valid-name');
      expect(wizardStore.validation.intent.isValid).toBe(true);
    });

    it('should reject invalid characters in name', () => {
      wizardStore.updateData('projectName', 'invalid name!');
      expect(wizardStore.validation.intent.isValid).toBe(false);
    });
  });
});
```

### Integration Tests

```typescript
// src/lib/workbench/__tests__/wizard-to-workbench.test.ts

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { wizardStore } from '../stores/wizard.svelte';
import { projectStore } from '../stores/project.svelte';

// Mock Tauri
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn().mockResolvedValue({
    projectId: 'test-123',
    path: '/test/path',
    filesCreated: ['README.md'],
  }),
}));

describe('Wizard to Workbench handoff', () => {
  beforeEach(() => {
    wizardStore.reset();
  });

  it('should create project from wizard data', async () => {
    const project = await projectStore.createFromWizard({
      projectName: 'test-project',
      projectDescription: 'A test project',
      projectType: 'web-app',
      complexity: 'moderate',
      primaryLanguage: 'typescript',
      secondaryLanguages: [],
      languagesConsidered: ['typescript'],
      selectedStack: { id: 'stack-1', name: 'SvelteKit' },
      stacksCompared: [],
      aiRecommendations: [],
      features: { testing: true },
      teamSize: 1,
      timeline: 'month',
      outputPath: '/test/path',
      generateReadme: true,
      initGit: true,
    });

    expect(project.name).toBe('test-project');
    expect(projectStore.hasActiveProject).toBe(true);
  });
});
```

### E2E Tests (Playwright)

```typescript
// tests/e2e/wizard-flow.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Wizard Flow', () => {
  test('should complete wizard and land in workbench', async ({ page }) => {
    await page.goto('/');
    
    // Click new project
    await page.click('text=New Project');
    
    // Step 1: Intent
    await page.fill('[data-testid="project-name"]', 'my-test-project');
    await page.click('text=Web Application');
    await page.click('text=Continue');
    
    // Step 2: Languages
    await page.click('text=TypeScript');
    await page.click('text=Continue');
    
    // Step 3: Stack
    await page.click('[data-testid="stack-sveltekit"]');
    await page.click('text=Continue');
    
    // Step 4: Config (skip)
    await page.click('text=Continue');
    
    // Step 5: Launch
    await page.click('text=Browse');
    // ... select directory
    await page.click('text=Create Project');
    
    // Should be in workbench
    await expect(page.locator('[data-testid="workbench"]')).toBeVisible();
    await expect(page.locator('text=my-test-project')).toBeVisible();
  });
});
```

---

## 12. Migration Checklist

### Pre-Migration

- [ ] Backup current codebase
- [ ] Create feature branch: `git checkout -b refactor/workbench-primary`
- [ ] Document current wizard state (71% complete)
- [ ] Identify reusable components from `/routes/wizard/`

### Phase 1: Foundation

- [ ] Create directory structure
- [ ] Create type definitions
- [ ] Create `wizard.svelte.ts` store
- [ ] Create `project.svelte.ts` store
- [ ] Create `userPreferences.svelte.ts` store
- [ ] Verify stores compile without errors

### Phase 2: Modal Wizard

- [ ] Create `NewProjectWizard.svelte`
- [ ] Create `WizardProgress.svelte`
- [ ] Migrate `StepIntent.svelte`
- [ ] Migrate `StepLanguages.svelte`
- [ ] Migrate `StepStack.svelte`
- [ ] Migrate `StepConfig.svelte`
- [ ] Migrate `StepLaunch.svelte`
- [ ] Test wizard modal opens/closes
- [ ] Test keyboard shortcuts (Escape, ⌘↵)

### Phase 3: Data Handoff

- [ ] Implement `createFromWizard()` in project store
- [ ] Implement `initializeWorkbenchFromProject()`
- [ ] Test context block generation
- [ ] Test prompt template generation
- [ ] Verify Tauri integration works
- [ ] Test learning tracking (non-blocking)

### Phase 4: Power User Flow

- [ ] Create `QuickCreateDialog.svelte`
- [ ] Create `WelcomeOverlay.svelte`
- [ ] Create `CommandPalette.svelte`
- [ ] Update `WorkbenchShell.svelte` with all entry points
- [ ] Test ⌘N keyboard shortcut
- [ ] Test ⌘K command palette
- [ ] Test recent projects list

### Phase 5: Cleanup

- [ ] Remove `/routes/wizard/` directory
- [ ] Remove old wizard stores from `/lib/stores/`
- [ ] Update `/routes/+page.svelte` to render WorkbenchShell
- [ ] Update any remaining imports
- [ ] Run full test suite
- [ ] Manual QA testing

### Post-Migration

- [ ] Update README.md
- [ ] Update ARCHITECTURE.md
- [ ] Create migration PR
- [ ] Code review
- [ ] Merge to main

---

## Appendix: Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘N` / `Ctrl+N` | New Project (Wizard or Quick Create based on preference) |
| `⌘O` / `Ctrl+O` | Open Project |
| `⌘K` / `Ctrl+K` | Command Palette |
| `⌘↵` / `Ctrl+Enter` | Continue (in wizard) or Run (in workbench) |
| `Escape` | Close modal |

### Store Access

```typescript
// Wizard store
import { wizardStore } from '$lib/workbench/stores/wizard.svelte';
wizardStore.open();
wizardStore.data.projectName;
wizardStore.nextStep();

// Project store
import { projectStore } from '$lib/workbench/stores/project.svelte';
projectStore.hasActiveProject;
projectStore.recentProjects;
await projectStore.createFromWizard(data);

// User preferences
import { userPreferencesStore } from '$lib/workbench/stores/userPreferences.svelte';
userPreferencesStore.skipWizard;
userPreferencesStore.update('skipWizard', true);
```

### Design System Colors

```css
/* Forge Color Palette */
--blacksteel-950: #09090b;
--gunmetal-900: #18181b;
--gunmetal-800: #27272a;
--gunmetal-700: #3f3f46;
--ember-600: #ea580c;
--ember-500: #f97316;
--ember-400: #fb923c;
```

---

**Document Version:** 1.0  
**Last Updated:** November 24, 2025  
**Author:** Claude (Anthropic)  
**For:** VibeForge Refactoring Project
