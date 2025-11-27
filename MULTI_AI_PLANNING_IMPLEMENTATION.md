# Multi-AI Planning System with Learning Layer
## Implementation Plan

**Version:** 1.0  
**Target Release:** VibeForge Core Infrastructure  
**Estimated AI Time:** 18-24 hours (Claude Code autonomous execution)  
**Dependencies:** DataForge, NeuroForge, PostgreSQL, existing model routing infrastructure

---

## Executive Summary

This implementation creates a sophisticated multi-AI planning workflow that orchestrates ChatGPT and Claude in a 4-stage review process, while building a learning layer that continuously improves model selection, time estimation, and iteration recommendations based on real execution data. This system forms the intelligence core of VibeForge's competitive moat.

**What it does:**
- Executes multi-stage planning workflows (ChatGPT → Claude → ChatGPT → Claude)
- Records detailed metrics for every planning session
- Learns optimal model selection based on task type and complexity
- Improves time estimates using EMA-based algorithms
- Provides data-driven recommendations for iteration counts
- Delivers two-file output ready for Claude Code execution

**Why it matters:**
- Creates learning moat through accumulated execution data
- Reduces planning time by selecting optimal models per stage
- Improves accuracy of time estimates over time
- Enables data-driven iteration on the planning process itself
- Positions VibeForge as "smarter with every use"

**Scope:**
- 3 database tables (planning_outcomes, model_performance, ai_estimation_feedback)
- 9 DataForge endpoints (recording + recommendations)
- 1 NeuroForge orchestration service with 4-stage prompt templates
- 2 NeuroForge API endpoints (standard + streaming)
- Background job processing for learning updates
- 100% test coverage across all components

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        VibeForge UI                         │
│                  (Workbench + Modal Wizard)                 │
└────────────────────┬────────────────────────────────────────┘
                     │ POST /api/v1/orchestrate/planning
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    NeuroForge Backend                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         orchestration_router.py                       │  │
│  │  - execute_planning_workflow()                        │  │
│  │  - execute_planning_workflow_stream() [SSE]           │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │    services/orchestration/multi_ai_executor.py        │  │
│  │                                                        │  │
│  │  4-Stage Pipeline:                                    │  │
│  │  1. ChatGPT (initial)  → model_router.execute()       │  │
│  │  2. Claude (review)    → model_router.execute()       │  │
│  │  3. ChatGPT (refine)   → model_router.execute()       │  │
│  │  4. Claude (final)     → model_router.execute()       │  │
│  └────────────────────────────┬──────────────────────────┘  │
└─────────────────────────────┼┼─────────────────────────────┘
                               ││
              ┌────────────────┘└────────────────┐
              │                                   │
     Fetch Recommendations            Record Outcomes (async)
              │                                   │
              ▼                                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    DataForge Backend                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              routers/learning.py                      │  │
│  │                                                        │  │
│  │  Recording:                                           │  │
│  │  - POST   /learning/planning-outcomes                 │  │
│  │  - PATCH  /learning/planning-outcomes/{id}/execution  │  │
│  │  - PATCH  /learning/planning-outcomes/{id}/feedback   │  │
│  │  - POST   /learning/estimation-feedback               │  │
│  │                                                        │  │
│  │  Recommendations:                                     │  │
│  │  - GET /learning/model-performance                    │  │
│  │  - GET /learning/recommendations/stage-models         │  │
│  │  - GET /learning/recommendations/time-estimate        │  │
│  │  - GET /learning/recommendations/iteration-count      │  │
│  └────────────────────┬──────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼──────────────────────────────────┐  │
│  │         Background Jobs (RabbitMQ/Celery)             │  │
│  │  - update_model_performance_from_outcome()            │  │
│  │  - recalculate_model_quality_with_execution()         │  │
│  │  - calculate_ema_metrics()                            │  │
│  └────────────────────┬──────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   PostgreSQL Database   │
              │                         │
              │  - planning_outcomes    │
              │  - model_performance    │
              │  - ai_estimation_feedback│
              └─────────────────────────┘
```

**Data Flow:**
1. VibeForge requests planning workflow execution
2. NeuroForge fetches learned recommendations from DataForge
3. Multi-AI executor runs 4-stage pipeline with optimal models
4. Each stage result is collected (model, tokens, duration, output)
5. Final two-file deliverable is parsed and returned
6. Background task records complete outcome to DataForge
7. DataForge updates model performance aggregates using EMA
8. Future requests benefit from accumulated learning

---

## Database Schema

### Table 1: planning_outcomes

Stores complete record of every planning session execution.

```sql
CREATE TABLE planning_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Session context
    session_id UUID NOT NULL,
    user_id VARCHAR(100),
    
    -- Request metadata
    workflow_type VARCHAR(50) NOT NULL,      -- 'multi_ai_planning'
    task_type VARCHAR(50),                   -- 'feature', 'refactor', 'bugfix'
    request_complexity VARCHAR(20),          -- 'simple', 'medium', 'complex'
    codebase_context JSONB,
    
    -- Stage-by-stage results
    stages JSONB NOT NULL,
    /*
    [
      { "stage": 1, "type": "initial", "model": "gpt-4", "provider": "openai",
        "duration_ms": 45000, "tokens_in": 1200, "tokens_out": 2500,
        "quality_score": null },
      { "stage": 2, "type": "review", "model": "claude-3-opus", "provider": "anthropic",
        "duration_ms": 32000, "tokens_in": 3700, "tokens_out": 1800,
        "issues_found": 3, "improvements": 5 },
      ...
    ]
    */
    
    -- Aggregates
    total_duration_ms INTEGER,
    total_tokens_used INTEGER,
    total_cost_cents INTEGER,
    iteration_count INTEGER DEFAULT 1,
    
    -- Execution outcome (filled after plan execution)
    execution_started BOOLEAN DEFAULT FALSE,
    execution_success BOOLEAN,
    execution_duration_seconds INTEGER,
    tasks_completed INTEGER,
    tasks_failed INTEGER,
    
    -- User feedback
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    plan_was_modified BOOLEAN DEFAULT FALSE,
    modification_extent REAL,               -- 0.0 to 1.0
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_planning_outcomes_session ON planning_outcomes(session_id);
CREATE INDEX idx_planning_outcomes_user ON planning_outcomes(user_id);
CREATE INDEX idx_planning_outcomes_created ON planning_outcomes(created_at DESC);
CREATE INDEX idx_planning_outcomes_task ON planning_outcomes(task_type, workflow_type);
```

### Table 2: model_performance

EMA-based aggregates tracking model effectiveness by dimensions.

```sql
CREATE TABLE model_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Dimensions (composite unique key)
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    stage_type VARCHAR(50) NOT NULL,        -- 'initial', 'review', 'refinement', 'final'
    task_type VARCHAR(50) DEFAULT 'general',
    
    -- Raw aggregates
    sample_count INTEGER DEFAULT 0,
    total_duration_ms BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    
    -- Calculated averages
    avg_duration_ms REAL,
    avg_tokens REAL,
    avg_quality_score REAL,                 -- 0.0 to 1.0
    success_rate REAL,                      -- 0.0 to 1.0
    
    -- EMA values (for adaptive learning)
    ema_duration_ms REAL,
    ema_quality REAL,
    ema_alpha REAL DEFAULT 0.1,             -- Learning rate
    
    -- Cost tracking
    avg_cost_cents REAL,
    
    UNIQUE(model, provider, stage_type, task_type)
);

CREATE INDEX idx_model_perf_lookup ON model_performance(model, provider, stage_type);
CREATE INDEX idx_model_perf_task ON model_performance(task_type, stage_type);
```

**EMA Update Logic:**
```python
# When new outcome recorded:
new_ema = (alpha * new_value) + ((1 - alpha) * old_ema)

# For quality scores derived from execution success:
quality = 0.9 if execution_success else 0.3
new_ema_quality = (0.1 * quality) + (0.9 * old_ema_quality)
```

### Table 3: ai_estimation_feedback

Tracks estimated vs actual execution time for continuous improvement.

```sql
CREATE TABLE ai_estimation_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Task context
    task_category VARCHAR(50) NOT NULL,     -- 'testing', 'type-safety', 'architecture'
    task_complexity VARCHAR(20),
    
    -- Estimation vs actual
    estimated_minutes REAL NOT NULL,
    actual_minutes REAL NOT NULL,
    accuracy_ratio REAL,                    -- actual / estimated
    
    -- Execution context
    executor_type VARCHAR(30) NOT NULL,     -- 'claude_code', 'human', 'cursor'
    model_used VARCHAR(100),
    codebase_lines INTEGER,
    
    -- Factors that affected estimate
    factors JSONB,
    
    -- User context
    user_id VARCHAR(100),
    session_id UUID
);

CREATE INDEX idx_estimation_task ON ai_estimation_feedback(task_category, executor_type);
CREATE INDEX idx_estimation_created ON ai_estimation_feedback(created_at DESC);
```

---

## API Specification

### NeuroForge Endpoints

#### POST /api/v1/orchestrate/planning

Execute multi-AI planning workflow (standard response).

**Request:**
```json
{
  "type": "feature",
  "title": "Add user authentication with JWT",
  "description": "Implement JWT-based auth with refresh tokens...",
  "code_context": "// Existing user model\nclass User { ... }",
  "analysis_results": {
    "complexity_score": 7.2,
    "estimated_files": 12
  },
  "complexity": "medium"
}
```

**Optional Config Override:**
```json
{
  "initial_model": "gpt-4-turbo",
  "refinement_model": "gpt-4",
  "max_iterations": 2
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "stages": [
    {
      "index": 0,
      "type": "initial",
      "model": "gpt-4",
      "duration_ms": 45230,
      "tokens": 3700,
      "metadata": {}
    },
    {
      "index": 1,
      "type": "review",
      "model": "claude-3-opus-20240229",
      "duration_ms": 32100,
      "tokens": 5500,
      "metadata": {
        "issues_found": 3,
        "improvements_suggested": 5,
        "questions_raised": 2
      }
    },
    {
      "index": 2,
      "type": "refinement",
      "model": "gpt-4",
      "duration_ms": 48900,
      "tokens": 6200,
      "metadata": {}
    },
    {
      "index": 3,
      "type": "final",
      "model": "claude-3-opus-20240229",
      "duration_ms": 67800,
      "tokens": 10500,
      "metadata": {}
    }
  ],
  "deliverable": {
    "implementation_plan": "# JWT Authentication Implementation\n\n## Executive Summary...",
    "claude_code_prompt": "# Claude Code Execution Prompt\n\nYou are implementing..."
  },
  "metrics": {
    "total_duration_ms": 194030,
    "total_tokens": 25900,
    "total_cost_cents": 89
  }
}
```

#### POST /api/v1/orchestrate/planning/stream

Execute planning workflow with SSE streaming.

**Request:** Same as above

**Response:** Server-Sent Events stream

```
data: {"type":"stage_start","index":0,"stage_type":"initial","model":"gpt-4"}

data: {"type":"stage_complete","index":0,"stage_type":"initial","duration_ms":45230,"tokens":3700,"preview":"# Initial Implementation Plan\n\n## Overview\nWe're implementing JWT..."}

data: {"type":"stage_start","index":1,"stage_type":"review","model":"claude-3-opus-20240229"}

data: {"type":"stage_complete","index":1,"stage_type":"review","duration_ms":32100,"tokens":5500,"preview":"## Review of Initial Plan\n\n### ✅ What's Good\n- Well..."}

...

data: {"type":"complete","session_id":"550e8400-...","deliverable":{...},"metrics":{...}}
```

### DataForge Endpoints

#### Recording Endpoints

##### POST /api/v1/learning/planning-outcomes

Record outcome of planning session.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_type": "multi_ai_planning",
  "task_type": "feature",
  "request_complexity": "medium",
  "stages": [
    {
      "stage": 0,
      "type": "initial",
      "model": "gpt-4",
      "provider": "openai",
      "duration_ms": 45230,
      "tokens_in": 1200,
      "tokens_out": 2500,
      "metadata": {}
    }
  ],
  "total_duration_ms": 194030,
  "total_tokens_used": 25900,
  "total_cost_cents": 89
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "recorded"
}
```

##### PATCH /api/v1/learning/planning-outcomes/{outcome_id}/execution

Update with execution results (called after Claude Code runs the plan).

**Request:**
```json
{
  "success": true,
  "duration_seconds": 3600,
  "tasks_completed": 12,
  "tasks_failed": 0
}
```

##### PATCH /api/v1/learning/planning-outcomes/{outcome_id}/feedback

Record user feedback.

**Request:**
```json
{
  "rating": 5,
  "feedback": "Excellent plan, worked perfectly with minimal changes",
  "plan_was_modified": false,
  "modification_extent": 0.05
}
```

##### POST /api/v1/learning/estimation-feedback

Batch record time estimation feedback.

**Request:**
```json
[
  {
    "task_category": "testing",
    "task_complexity": "medium",
    "estimated_minutes": 45,
    "actual_minutes": 52,
    "executor_type": "claude_code",
    "model_used": "claude-3-opus",
    "codebase_lines": 15000,
    "factors": {
      "had_tests": false,
      "files_touched": 8,
      "retries_needed": 1
    }
  }
]
```

#### Recommendation Endpoints

##### GET /api/v1/learning/model-performance

Query model performance aggregates.

**Query Params:**
- `stage_type` (optional): Filter by stage type
- `task_type` (optional): Filter by task type

**Response:**
```json
[
  {
    "model": "gpt-4",
    "provider": "openai",
    "stage_type": "initial",
    "task_type": "feature",
    "sample_count": 247,
    "avg_duration_ms": 43200,
    "avg_tokens": 3500,
    "avg_quality_score": 0.82,
    "success_rate": 0.91,
    "ema_duration_ms": 42800,
    "ema_quality": 0.84,
    "avg_cost_cents": 12
  }
]
```

##### GET /api/v1/learning/recommendations/stage-models

Get recommended models for each stage based on learning.

**Query Params:**
- `task_type` (default: "general")

**Response:**
```json
{
  "initial": {
    "model": "gpt-4",
    "provider": "openai",
    "reason": "Best balance of speed (43s avg) and quality (0.84) for initial planning",
    "confidence": 0.87
  },
  "review": {
    "model": "claude-3-opus-20240229",
    "provider": "anthropic",
    "reason": "Consistently finds 2.3x more issues than alternatives",
    "confidence": 0.92
  },
  "refinement": {
    "model": "gpt-4",
    "provider": "openai",
    "reason": "Excels at incorporating feedback (0.89 quality)",
    "confidence": 0.85
  },
  "final": {
    "model": "claude-3-opus-20240229",
    "provider": "anthropic",
    "reason": "Produces most complete deliverables (0.91 quality)",
    "confidence": 0.94
  },
  "confidence": 0.89,
  "based_on_samples": 247
}
```

##### GET /api/v1/learning/recommendations/time-estimate

Get time estimate based on historical data.

**Query Params:**
- `task_category`: e.g., "testing", "type-safety"
- `executor_type` (default: "claude_code")
- `complexity` (default: "medium")

**Response:**
```json
{
  "estimated_minutes": 48,
  "confidence": 0.78,
  "confidence_interval": [42, 54],
  "based_on_samples": 156,
  "note": null
}
```

##### GET /api/v1/learning/recommendations/iteration-count

Recommend optimal ChatGPT ↔ Claude iterations.

**Query Params:**
- `task_type` (default: "general")
- `complexity` (default: "medium")

**Response:**
```json
{
  "recommended": 2,
  "min_viable": 1,
  "diminishing_returns": 4,
  "confidence": 0.82,
  "based_on_samples": 203,
  "note": "Quality improvement plateaus after 4 iterations"
}
```

---

## File Structure

```
dataforge_backend/
├── alembic/
│   └── versions/
│       └── xxx_add_learning_tables.py          # NEW: Migration
├── models/
│   ├── planning_outcome.py                     # NEW: SQLAlchemy model
│   ├── model_performance.py                    # NEW: SQLAlchemy model
│   └── ai_estimation_feedback.py               # NEW: SQLAlchemy model
├── routers/
│   └── learning.py                             # NEW: 9 endpoints
├── services/
│   ├── learning/
│   │   ├── performance_calculator.py           # NEW: EMA calculations
│   │   ├── recommendation_engine.py            # NEW: Model selection logic
│   │   └── time_estimator.py                   # NEW: Time estimation logic
│   └── background/
│       └── learning_jobs.py                    # NEW: Background processing
├── schemas/
│   ├── planning_outcome.py                     # NEW: Pydantic schemas
│   └── learning_recommendations.py             # NEW: Pydantic schemas
└── tests/
    ├── test_routers/
    │   └── test_learning.py                    # NEW: Router tests
    └── test_services/
        └── test_learning/
            ├── test_performance_calculator.py  # NEW
            ├── test_recommendation_engine.py   # NEW
            └── test_time_estimator.py          # NEW

neuroforge_backend/
├── services/
│   └── orchestration/
│       ├── multi_ai_executor.py                # NEW: Core orchestration
│       ├── prompt_templates.py                 # NEW: Stage prompts
│       └── deliverable_parser.py               # NEW: Two-file parsing
├── routers/
│   └── orchestration_router.py                 # NEW: 2 endpoints
├── clients/
│   └── dataforge_client.py                     # MODIFIED: Add learning methods
└── tests/
    ├── test_services/
    │   └── test_orchestration/
    │       ├── test_multi_ai_executor.py       # NEW
    │       └── test_deliverable_parser.py      # NEW
    └── test_routers/
        └── test_orchestration_router.py        # NEW
```

---

## Implementation Phases

### Phase 1: DataForge Learning Tables & Models (2-3h AI time)

**Objective:** Set up database schema and SQLAlchemy models.

**Tasks:**
1. Create Alembic migration `xxx_add_learning_tables.py`
   - Add all three tables with proper constraints
   - Add all indexes
   - Run migration locally and verify

2. Create SQLAlchemy models
   - `models/planning_outcome.py` with JSONB support
   - `models/model_performance.py` with unique constraint
   - `models/ai_estimation_feedback.py`
   - Proper relationships and type hints

3. Create Pydantic schemas
   - `schemas/planning_outcome.py` (Create, Update, Response)
   - `schemas/learning_recommendations.py` (all recommendation types)
   - Validation rules and examples

**Files Created:**
- `dataforge_backend/alembic/versions/xxx_add_learning_tables.py`
- `dataforge_backend/models/planning_outcome.py`
- `dataforge_backend/models/model_performance.py`
- `dataforge_backend/models/ai_estimation_feedback.py`
- `dataforge_backend/schemas/planning_outcome.py`
- `dataforge_backend/schemas/learning_recommendations.py`

**Verification:**
```bash
# Run migration
cd dataforge_backend
alembic upgrade head

# Verify tables exist
psql -d dataforge_dev -c "\dt planning_outcomes"
psql -d dataforge_dev -c "\d planning_outcomes"
psql -d dataforge_dev -c "\d model_performance"
psql -d dataforge_dev -c "\d ai_estimation_feedback"

# Verify indexes
psql -d dataforge_dev -c "\di idx_planning_outcomes_*"
```

**Tests:**
- `test_models/test_planning_outcome_model.py`
- `test_schemas/test_planning_outcome_schemas.py`
- 100% coverage required

**Git Checkpoint:** `git tag phase1-learning-tables`

---

### Phase 2: DataForge Recording Endpoints (3-4h AI time)

**Objective:** Implement endpoints for recording planning outcomes and feedback.

**Tasks:**
1. Create `routers/learning.py` with recording endpoints
   - POST `/learning/planning-outcomes`
   - PATCH `/learning/planning-outcomes/{id}/execution`
   - PATCH `/learning/planning-outcomes/{id}/feedback`
   - POST `/learning/estimation-feedback`
   - Proper error handling (404, validation errors)
   - Background task triggers

2. Create background job services
   - `services/background/learning_jobs.py`
   - `update_model_performance_from_outcome()` function
   - `recalculate_model_quality_with_execution()` function
   - Celery task decorators (or RabbitMQ direct)

3. Integration with existing DataForge auth
   - Use existing `get_current_user` dependency
   - Proper user_id association

**Files Created:**
- `dataforge_backend/routers/learning.py` (partial - 4 endpoints)
- `dataforge_backend/services/background/learning_jobs.py`

**Verification:**
```bash
# Start DataForge server
cd dataforge_backend
uvicorn main:app --reload --port 8001

# Test recording endpoint
curl -X POST http://localhost:8001/api/v1/learning/planning-outcomes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id":"550e8400-...","workflow_type":"multi_ai_planning",...}'

# Verify record in DB
psql -d dataforge_dev -c "SELECT * FROM planning_outcomes ORDER BY created_at DESC LIMIT 1;"
```

**Tests:**
- `test_routers/test_learning.py` (recording endpoints)
- Mock database sessions
- Test error cases (404, validation)
- 100% coverage required

**Git Checkpoint:** `git tag phase2-recording-endpoints`

---

### Phase 3: DataForge Learning Logic (4-5h AI time)

**Objective:** Implement EMA calculations and recommendation algorithms.

**Tasks:**
1. Create `services/learning/performance_calculator.py`
   - `update_model_performance(outcome)` - Insert/update with EMA
   - `calculate_ema(old_value, new_value, alpha)` - Core EMA logic
   - Handle initial values (when sample_count = 0)
   - Atomic upsert operations

2. Create `services/learning/recommendation_engine.py`
   - `select_best_model_for_stage(stage_type, task_type, performances)`
   - Scoring algorithm: `score = (ema_quality * 0.7) + (success_rate * 0.3) - (normalized_cost * 0.1)`
   - Confidence calculation based on sample size
   - Fallback to defaults when insufficient data

3. Create `services/learning/time_estimator.py`
   - `calculate_ema_time_estimate(feedback_items, complexity)`
   - Complexity multipliers (simple: 0.7, medium: 1.0, complex: 1.5)
   - Confidence interval calculation (±20% with 80% confidence)
   - Default estimates when data insufficient

4. Integrate with background jobs
   - Call performance calculator from jobs
   - Handle concurrent updates safely

**Files Created:**
- `dataforge_backend/services/learning/performance_calculator.py`
- `dataforge_backend/services/learning/recommendation_engine.py`
- `dataforge_backend/services/learning/time_estimator.py`

**Verification:**
```python
# Test EMA calculation
from services.learning.performance_calculator import calculate_ema

old_ema = 45000  # ms
new_value = 52000  # ms
alpha = 0.1

result = calculate_ema(old_ema, new_value, alpha)
assert result == 45700  # (0.1 * 52000) + (0.9 * 45000)

# Test recommendation with mock data
from services.learning.recommendation_engine import select_best_model_for_stage
# ... create mock performances
best = select_best_model_for_stage("initial", "feature", performances)
assert best.model == "gpt-4"
```

**Tests:**
- `test_services/test_learning/test_performance_calculator.py`
- `test_services/test_learning/test_recommendation_engine.py`
- `test_services/test_learning/test_time_estimator.py`
- Test edge cases: no data, single sample, extreme values
- 100% coverage required

**Git Checkpoint:** `git tag phase3-learning-logic`

---

### Phase 4: DataForge Recommendation Endpoints (2-3h AI time)

**Objective:** Complete learning router with query/recommendation endpoints.

**Tasks:**
1. Add recommendation endpoints to `routers/learning.py`
   - GET `/learning/model-performance`
   - GET `/learning/recommendations/stage-models`
   - GET `/learning/recommendations/time-estimate`
   - GET `/learning/recommendations/iteration-count`

2. Integrate with learning services
   - Call performance_calculator for aggregates
   - Call recommendation_engine for model selection
   - Call time_estimator for time predictions

3. Implement iteration analysis logic
   - Query planning_outcomes by iteration_count
   - Analyze quality improvement per iteration
   - Find diminishing returns threshold

**Files Modified:**
- `dataforge_backend/routers/learning.py` (add 4 endpoints)

**Verification:**
```bash
# Query model performance
curl http://localhost:8001/api/v1/learning/model-performance?stage_type=review

# Get stage recommendations
curl http://localhost:8001/api/v1/learning/recommendations/stage-models?task_type=feature

# Get time estimate
curl http://localhost:8001/api/v1/learning/recommendations/time-estimate?task_category=testing&executor_type=claude_code
```

**Tests:**
- `test_routers/test_learning.py` (recommendation endpoints)
- Mock learning services
- Test with various data scenarios
- 100% coverage required

**Git Checkpoint:** `git tag phase4-recommendation-endpoints`

---

### Phase 5: NeuroForge Multi-AI Executor (5-6h AI time)

**Objective:** Core orchestration service with 4-stage pipeline.

**Tasks:**
1. Create `services/orchestration/prompt_templates.py`
   - `STAGE_1_INITIAL_PLAN_TEMPLATE`
   - `STAGE_2_REVIEW_TEMPLATE`
   - `STAGE_3_REFINEMENT_TEMPLATE`
   - `STAGE_4_FINAL_TEMPLATE`
   - Template variables and formatting

2. Create `services/orchestration/multi_ai_executor.py`
   - `MultiAIExecutor` class with default stage configs
   - `execute_planning_workflow()` method
   - Stage execution loop with model_router calls
   - Context accumulation between stages
   - Progress callbacks (on_stage_start, on_stage_complete)
   - Cost calculation
   - Error handling and retries

3. Create `services/orchestration/deliverable_parser.py`
   - `parse_two_file_deliverable(final_output)` function
   - Extract IMPLEMENTATION_PLAN.md content
   - Extract CLAUDE_CODE_PROMPT.md content
   - Handle various markdown formats

4. Update `clients/dataforge_client.py`
   - Add `get_stage_recommendations(task_type)` method
   - Add `record_planning_outcome(outcome)` method
   - Error handling with fallback to defaults

**Files Created:**
- `neuroforge_backend/services/orchestration/prompt_templates.py`
- `neuroforge_backend/services/orchestration/multi_ai_executor.py`
- `neuroforge_backend/services/orchestration/deliverable_parser.py`

**Files Modified:**
- `neuroforge_backend/clients/dataforge_client.py`

**Verification:**
```python
# Test multi-AI executor
from services.orchestration.multi_ai_executor import multi_ai_executor

result = await multi_ai_executor.execute_planning_workflow(
    request={
        "type": "feature",
        "title": "Test feature",
        "description": "Test description",
    }
)

assert result.success == True
assert len(result.stages) == 4
assert result.stages[0].stage_type == "initial"
assert result.stages[1].stage_type == "review"
assert result.final_output is not None
```

**Tests:**
- `test_services/test_orchestration/test_multi_ai_executor.py`
- `test_services/test_orchestration/test_deliverable_parser.py`
- Mock model_router calls
- Test stage progression
- Test error handling
- 100% coverage required

**Git Checkpoint:** `git tag phase5-multi-ai-executor`

---

### Phase 6: NeuroForge Orchestration Endpoints (3-4h AI time)

**Objective:** Expose orchestration via FastAPI with streaming support.

**Tasks:**
1. Create `routers/orchestration_router.py`
   - POST `/orchestrate/planning` (standard)
   - POST `/orchestrate/planning/stream` (SSE)
   - Request/response models
   - Config override handling
   - Background task for DataForge recording

2. Implement SSE streaming
   - `StreamingResponse` with SSE format
   - Event types: stage_start, stage_complete, complete
   - Proper event formatting (`data: {json}\n\n`)

3. Integration with DataForge
   - Fetch recommendations before execution
   - Record outcome asynchronously
   - Graceful degradation on DataForge unavailable

4. Update NeuroForge main app
   - Include orchestration router
   - Ensure proper CORS for SSE

**Files Created:**
- `neuroforge_backend/routers/orchestration_router.py`

**Files Modified:**
- `neuroforge_backend/main.py` (include router)

**Verification:**
```bash
# Start NeuroForge server
cd neuroforge_backend
uvicorn main:app --reload --port 8002

# Test standard endpoint
curl -X POST http://localhost:8002/api/v1/orchestrate/planning \
  -H "Content-Type: application/json" \
  -d '{"type":"feature","title":"Test","description":"Test desc"}'

# Test streaming endpoint
curl -N http://localhost:8002/api/v1/orchestrate/planning/stream \
  -H "Content-Type: application/json" \
  -d '{"type":"feature","title":"Test","description":"Test desc"}'
```

**Tests:**
- `test_routers/test_orchestration_router.py`
- Mock multi_ai_executor
- Test standard response
- Test SSE streaming
- Test error cases
- 100% coverage required

**Git Checkpoint:** `git tag phase6-orchestration-endpoints`

---

### Phase 7: Integration & E2E Testing (2-3h AI time)

**Objective:** End-to-end integration testing across services.

**Tasks:**
1. Create integration test suite
   - `tests/integration/test_learning_flow.py`
   - Test complete workflow: plan → record → query recommendations
   - Test DataForge ↔ NeuroForge interaction

2. Create E2E test scenarios
   - Simple feature request
   - Complex refactor request
   - Multiple iterations scenario
   - Execution feedback loop

3. Performance testing
   - Measure total workflow duration
   - Verify EMA calculations converge correctly
   - Check database query performance

4. Documentation
   - Update API documentation
   - Add usage examples
   - Document recommendation confidence thresholds

**Files Created:**
- `tests/integration/test_learning_flow.py`
- `docs/MULTI_AI_PLANNING.md`

**Verification:**
```bash
# Run integration tests
pytest tests/integration/test_learning_flow.py -v

# Full test suite
pytest --cov=. --cov-report=html

# Verify 100% coverage
open htmlcov/index.html
```

**Tests:**
- E2E scenarios with real database (test DB)
- Mock external model APIs
- Verify data flows correctly
- 100% coverage across entire feature

**Git Checkpoint:** `git tag phase7-integration-complete`

---

## Testing Strategy

### Unit Tests (Required for 100% Coverage)

**DataForge:**
- All model methods (create, update, relationships)
- All schema validations
- All router endpoints (mock DB)
- All learning service methods (pure logic)
- Background job handlers

**NeuroForge:**
- Multi-AI executor stage progression
- Prompt template formatting
- Deliverable parsing (various formats)
- Router endpoints (mock executor)
- DataForge client methods

### Integration Tests

- Complete planning workflow with both services
- Learning feedback loop
- Recommendation query after multiple outcomes
- EMA convergence verification
- Background job execution

### Test Data

Create fixtures in `tests/fixtures/`:
- `planning_outcomes.json` - Sample outcomes
- `model_performances.json` - Sample performance data
- `stage_results.json` - Sample stage results
- `final_deliverables.json` - Sample two-file outputs

### Mock Strategies

**Model API Calls:**
```python
@pytest.fixture
def mock_model_router(mocker):
    mock = mocker.patch('services.model_router.model_router.execute')
    mock.return_value = ModelResponse(
        output="Test output",
        tokens_in=100,
        tokens_out=200,
        duration_ms=5000
    )
    return mock
```

**Database Sessions:**
```python
@pytest.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session
        await session.rollback()
```

### Coverage Thresholds

- Overall: 100% (Forge product standard)
- Per file: 100%
- Branch coverage: 95%+

---

## Success Criteria

### Functional Requirements

✅ Planning workflow executes 4 stages successfully  
✅ Each stage uses correct model (GPT-4 or Claude)  
✅ Stage results recorded with full metrics  
✅ Two-file deliverable parsed correctly  
✅ Outcomes stored in DataForge  
✅ Model performance aggregates updated via EMA  
✅ Recommendations query returns learned models  
✅ Time estimates improve with feedback  
✅ Streaming endpoint delivers SSE correctly  
✅ Background jobs process asynchronously  

### Performance Requirements

✅ Total workflow completes in < 4 minutes (typical)  
✅ Recommendation queries respond in < 200ms  
✅ Background jobs complete within 5 seconds  
✅ Database queries use proper indexes (explain analyze)  
✅ No N+1 query issues  

### Quality Requirements

✅ 100% test coverage across all components  
✅ All tests passing  
✅ No type errors (mypy)  
✅ Code formatted (black, isort)  
✅ API documentation complete  
✅ Error handling comprehensive  

### Data Quality

✅ EMA calculations mathematically correct  
✅ Recommendations converge with > 50 samples  
✅ Confidence scores accurate  
✅ No data loss in background processing  
✅ Proper transaction handling  

---

## Deployment Considerations

### Environment Variables

**DataForge:**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dataforge
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672
```

**NeuroForge:**
```env
DATAFORGE_API_URL=http://localhost:8001
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "add learning tables"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Monitoring

**Key Metrics:**
- Planning workflow duration (p50, p95, p99)
- Stage success rates by model
- Recommendation confidence trends
- EMA convergence speed
- Background job queue depth
- API error rates

**Alerts:**
- Planning workflow failures
- DataForge unavailable
- Model API errors
- Background job failures
- Database connection issues

---

## Future Enhancements

### Phase 8 (Post-MVP)

1. **Advanced Iteration Logic**
   - Automatic iteration based on quality thresholds
   - Early stopping when quality plateaus
   - Dynamic model selection per iteration

2. **User Preferences**
   - Save preferred models per user
   - Custom quality thresholds
   - Cost vs quality trade-off settings

3. **A/B Testing Framework**
   - Test different prompt templates
   - Compare model combinations
   - Statistical significance testing

4. **Quality Scoring**
   - Automated quality assessment of plans
   - User rating predictions
   - Plan complexity analysis

5. **Multi-User Learning**
   - Team-level aggregates
   - Organization-wide recommendations
   - Privacy-preserving learning

---

## Appendix A: EMA Algorithm Details

### Exponential Moving Average

```python
def calculate_ema(old_ema: float, new_value: float, alpha: float = 0.1) -> float:
    """
    Calculate exponential moving average.
    
    Args:
        old_ema: Previous EMA value
        new_value: New sample value
        alpha: Learning rate (0-1, typically 0.1)
    
    Returns:
        Updated EMA value
    
    Formula:
        new_ema = (alpha * new_value) + ((1 - alpha) * old_ema)
    
    Example:
        old_ema = 45000  # 45 seconds
        new_value = 52000  # 52 seconds
        alpha = 0.1
        
        new_ema = (0.1 * 52000) + (0.9 * 45000)
                = 5200 + 40500
                = 45700  # 45.7 seconds
    """
    return (alpha * new_value) + ((1 - alpha) * old_ema)
```

### Choosing Alpha

- **α = 0.1** (default): Moderate learning, smooth trends
- **α = 0.2**: Faster adaptation to changes
- **α = 0.05**: Very stable, slow to change

### Handling Initial Values

```python
if sample_count == 0:
    # First sample: EMA = value
    ema_value = new_value
elif sample_count == 1:
    # Second sample: Simple average
    ema_value = (old_ema + new_value) / 2
else:
    # Subsequent samples: Use EMA formula
    ema_value = calculate_ema(old_ema, new_value, alpha)
```

---

## Appendix B: Cost Calculation

### Token Pricing (as of 2024)

| Model | Provider | Input (per 1M) | Output (per 1M) |
|-------|----------|----------------|-----------------|
| GPT-4 | OpenAI | $30 | $60 |
| Claude 3 Opus | Anthropic | $15 | $75 |
| Claude 3 Sonnet | Anthropic | $3 | $15 |

### Calculation Example

```python
def calculate_stage_cost(tokens_in: int, tokens_out: int, model: str, provider: str) -> int:
    """Calculate cost in cents for a stage."""
    
    pricing = {
        ("gpt-4", "openai"): {"input": 3.0, "output": 6.0},  # per 1K tokens, in cents
        ("claude-3-opus-20240229", "anthropic"): {"input": 1.5, "output": 7.5},
    }
    
    key = (model, provider)
    if key not in pricing:
        return 0
    
    p = pricing[key]
    cost_cents = (tokens_in / 1000 * p["input"]) + (tokens_out / 1000 * p["output"])
    
    return int(cost_cents)

# Example stage:
# Input: 1200 tokens, Output: 2500 tokens, Model: GPT-4
cost = calculate_stage_cost(1200, 2500, "gpt-4", "openai")
# = (1200/1000 * 3.0) + (2500/1000 * 6.0)
# = 3.6 + 15.0
# = 18.6 cents
```

### Typical Workflow Cost

4-stage workflow estimate:
- Stage 1 (GPT-4): ~18 cents
- Stage 2 (Claude Opus): ~35 cents
- Stage 3 (GPT-4): ~22 cents
- Stage 4 (Claude Opus): ~60 cents
- **Total: ~$1.35 per workflow**

---

## Appendix C: Recommendation Scoring

### Model Selection Algorithm

```python
def score_model(performance: ModelPerformance) -> float:
    """
    Calculate composite score for model selection.
    
    Weights:
    - Quality (70%): Most important for plan quality
    - Success Rate (30%): Reliability matters
    - Cost (-10%): Slight penalty for expensive models
    
    Returns score between 0-1 (higher is better)
    """
    
    # Normalize cost to 0-1 scale (inverse, so lower cost = higher score)
    # Assume max cost is 100 cents
    normalized_cost = 1.0 - min(performance.avg_cost_cents / 100, 1.0)
    
    score = (
        (performance.ema_quality * 0.7) +
        (performance.success_rate * 0.3) -
        (normalized_cost * 0.1)
    )
    
    return max(0.0, min(1.0, score))


def select_best_model(
    stage_type: str,
    task_type: str,
    performances: list[ModelPerformance]
) -> ModelRecommendation:
    """Select best model for a stage based on learned data."""
    
    # Filter relevant performances
    relevant = [
        p for p in performances
        if p.stage_type == stage_type and 
           p.task_type in [task_type, "general"]
    ]
    
    if not relevant:
        return get_default_recommendation(stage_type)
    
    # Score and sort
    scored = [(score_model(p), p) for p in relevant]
    scored.sort(reverse=True, key=lambda x: x[0])
    
    best_score, best_perf = scored[0]
    
    # Calculate confidence based on sample size
    confidence = min(best_perf.sample_count / 100, 1.0)
    
    return ModelRecommendation(
        model=best_perf.model,
        provider=best_perf.provider,
        confidence=confidence,
        reason=f"Score: {best_score:.2f} (quality: {best_perf.ema_quality:.2f}, success: {best_perf.success_rate:.2f})"
    )
```

---

## Notes

- All timestamps are stored in UTC
- JSONB fields allow schema evolution without migrations
- Background jobs are idempotent and can be retried safely
- EMA calculations are atomic using database transactions
- Recommendations gracefully fall back to defaults when insufficient data
- The system improves continuously with each workflow execution
- Cost tracking enables future cost optimization features

**End of Implementation Plan**
