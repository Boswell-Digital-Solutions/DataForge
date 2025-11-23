# NeuroForge Learning Layer + DataForge Schema (Combined Document)

## Overview
This single document combines:
- **NeuroForge Learning Layer Blueprint**
- **DataForge Schema for Learning + Adaptation**

It represents the complete adaptive intelligence layer that allows NeuroForge to improve over time based on:
- language usage
- stack preferences
- model performance
- project outcomes
- scaffolding success
- historical context

---

# ============================================================
# 1. NeuroForge Learning Layer — Design Blueprint
# ============================================================

## Goals
- Improve stack recommendations through history and context.
- Optimize LLM model routing per language/task.
- Track user preferences across the Forge ecosystem.
- Power personalized project scaffolding.
- Give explainable recommendations using past data.
- Enable adaptive behavior without training new models.

---

## Architecture Overview

NeuroForge acts as:
- an orchestrator  
- a reasoning layer  
- a central decision-making engine  

DataForge acts as:
- a long-term memory store  
- a structured knowledge graph  
- a historical project+performance database  

VibeForge acts as:
- the interface  
- the project wizard  
- the front-end for automation triggers  

---

## Learning Flow

1. **User works in VibeForge**  
   - Selects languages  
   - Selects a stack  
   - Scaffolds project  
   - Generates code  
   - Tests / builds / deploys  

2. **NeuroForge logs all of it**  
   - Stored inside DataForge  
   - Build/test success  
   - LLM model used  
   - Fix attempts  
   - User overrides  

3. **Next time**  
   NeuroForge queries DataForge:

   - Similar projects  
   - Most-used languages  
   - Most successful stacks  
   - Preferred frameworks  
   - Model performance by language  

4. **Stack Advisor prompt includes this history**, enabling context-aware recommendations.

---

## Learning Components

### 1. Logging Layer
Captured events:
- project creation  
- languages chosen  
- stacks recommended vs chosen  
- scaffolding generated  
- code repair attempts  
- build/test pass/fail  
- latency/cost metrics  
- model selected per task  

All logs stored in structured JSON inside DataForge.

---

### 2. Query Layer

Before advising:
- look up past similar projects  
- compare language overlap  
- compare project type  
- evaluate stack success  
- retrieve model performance  
- aggregate usage patterns  

This builds the **experience_context** object.

---

### 3. Experience Context (Example)

```json
{
  "user_language_preferences": ["python", "typescript"],
  "common_stacks_for_these_languages": [
    { "stack_profile": "forge-web-stack", "success_score": 0.93 },
    { "stack_profile": "rust-tauri-stack", "success_score": 0.81 }
  ],
  "similar_projects": [
    {
      "project_type": "desktop-app",
      "languages": ["rust", "typescript"],
      "stack_profile": "rust-tauri-stack",
      "outcome_rating": 4.2
    }
  ],
  "model_performance_by_language": [
    { "language": "python", "best_models": ["claude-3.5", "gpt-4.1"] },
    { "language": "typescript", "best_models": ["gpt-4.1"] }
  ]
}
```

---

### 4. Scoring Layer (Simple, Effective)

Stack score =  
- base profile score  
- + language match bonus  
- + project type match bonus  
- + history performance bonus  
- + usage frequency weight  
- + success/failure penalty  

A lightweight scoring algorithm avoids overfitting and keeps behavior predictable.

---

### 5. Enhanced Stack Advisor Prompt

```text
You are the Stack Advisor for the VibeForge ecosystem.

PROJECT:
- Name: {{project_name}}
- Type: {{project_type}}
- Languages: {{selected_languages}}
- Priorities: {{priorities}}

USER HISTORY:
{{experience_context}}

AVAILABLE STACKS:
{{stack_profiles}}

TASK:
Rank the top 3 stacks.
Explain reasoning referencing user history, languages, and success metrics.
Return JSON with primary recommendation + ranked list.
```

---

### MVP vs Future

**MVP:**
- log language + stack choices  
- recommend stacks using basic scoring  
- include minimal history in prompts  

**Future:**
- performance-weighted stack routing  
- model routing analytics  
- org/team learning  
- confidence scoring  
- drift detection  
- real-time monitoring  

---

# ============================================================
# 2. DataForge Schema for the Learning Layer
# ============================================================

## Purpose
DataForge stores all relevant historical data for:
- project metadata  
- stack choices  
- model performance  
- test/build outcomes  
- user language preferences  
- scaffolding history  

This schema ensures NeuroForge has high-quality, queryable memory.

---

# Tables / Collections

## 1. `projects`

Tracks each project’s core identity.

```json
{
  "project_id": "vibeforge-core",
  "name": "VibeForge Core",
  "project_type": "desktop-app",
  "created_at": "2025-10-10T12:00:00Z",
  "languages": ["typescript", "python"],
  "stack_profile": "forge-web-stack",
  "priority_flags": ["ai-heavy", "linux-first"],
  "status": "active"
}
```

---

## 2. `project_sessions`

Tracks each run of the Project Wizard.

```json
{
  "session_id": "sess_001",
  "project_id": "vibeforge-core",
  "timestamp": "2025-12-01T15:20:00Z",
  "selected_languages": ["typescript", "python"],
  "suggested_stacks": ["forge-web-stack", "nextjs-fastapi-hybrid"],
  "chosen_stack": "forge-web-stack",
  "user_overrode_suggestion": false
}
```

---

## 3. `stack_outcomes`

Historical success/failure for recommended stacks.

```json
{
  "project_id": "vibeforge-core",
  "stack_profile": "forge-web-stack",
  "languages": ["typescript", "python"],
  "period": "2025-Q4",
  "metrics": {
    "build_success_rate": 0.96,
    "test_pass_rate": 0.88,
    "num_fix_iterations": 5,
    "num_generated_scaffolds": 3
  },
  "subjective_score": 4.5
}
```

---

## 4. `model_performance`

Tracks how well each LLM performs at code generation.

```json
{
  "model_name": "gpt-4.1",
  "task_type": "codegen",
  "language": "rust",
  "framework": "axum",
  "metrics": {
    "avg_fix_iterations": 1.2,
    "avg_user_rating": 4.7,
    "num_samples": 23
  },
  "last_updated": "2025-11-20T10:00:00Z"
}
```

---

## 5. `language_preferences`

Aggregated historical per-user preferences.

```json
{
  "user_id": "charles",
  "ranked_languages": [
    { "language": "python", "weight": 0.9 },
    { "language": "typescript", "weight": 0.8 },
    { "language": "rust", "weight": 0.6 }
  ],
  "ranked_stacks": [
    { "stack_profile": "forge-web-stack", "weight": 0.95 },
    { "stack_profile": "rust-tauri-stack", "weight": 0.7 }
  ],
  "last_updated": "2025-11-21T14:20:00Z"
}
```

---

# Index / Performance Recommendations

For fast queries:

- `projects`:  
  - `project_type`, `languages`, `stack_profile`

- `project_sessions`:  
  - `project_id`, `timestamp`

- `stack_outcomes`:  
  - `stack_profile`, `period`

- `model_performance`:  
  - `model_name`, `language`, `task_type`

- `language_preferences`:  
  - `user_id`

---

# Future Schema Extensions
- Organizational learning  
- Team-level preference tracking  
- Multiple model benchmarks  
- Predictive scoring  
- Time-series trend analytics  

---

# END OF DOCUMENT
