# Phase 3: NeuroForge Learning Layer Integration

## Overview

Integrate adaptive intelligence into VibeForge by connecting to DataForge for historical learning, allowing the system to improve recommendations based on actual usage patterns and outcomes.

---

## Prerequisites

- ✅ Phase 1: Stack Profiles & Language System (COMPLETE)
- ✅ Phase 2.1: Wizard Architecture (COMPLETE)
- 🚧 Phase 2.2-2.6: Complete Wizard Implementation (IN PROGRESS)

---

## Phase 3 Milestones

### Milestone 3.1: DataForge Schema Implementation (3-4 days)

**Goal**: Set up the persistence layer in DataForge to track projects, sessions, and outcomes.

**Tasks**:

1. Create Alembic migrations for new tables:
   - `projects` - Core project metadata
   - `project_sessions` - Wizard interaction history
   - `stack_outcomes` - Stack performance metrics
   - `model_performance` - LLM model effectiveness tracking
   - `language_preferences` - User language history

2. Create Pydantic models for each table:
   - `ProjectCreate`, `ProjectResponse`
   - `SessionCreate`, `SessionResponse`
   - `OutcomeCreate`, `OutcomeResponse`
   - `ModelPerformanceCreate`, `ModelPerformanceResponse`
   - `LanguagePreferenceResponse`

3. Build CRUD services:
   - `ProjectService` - Project lifecycle management
   - `SessionService` - Wizard session tracking
   - `OutcomeService` - Success/failure recording
   - `PerformanceService` - Model metrics aggregation
   - `PreferenceService` - User preference analysis

4. Create API endpoints in DataForge:
   - `POST /api/projects` - Create new project record
   - `GET /api/projects/{id}` - Retrieve project details
   - `POST /api/sessions` - Log wizard session
   - `POST /api/outcomes` - Record build/test outcomes
   - `GET /api/preferences/{user_id}` - Get user preferences
   - `GET /api/analytics/stack-success` - Stack success rates
   - `GET /api/analytics/language-trends` - Language usage trends

**Deliverables**:

- 5 new database tables with proper indexes
- Complete CRUD API layer
- Test suite with 95%+ coverage
- API documentation

---

### Milestone 3.2: VibeForge Backend Integration (2-3 days)

**Goal**: Connect VibeForge backend to DataForge for logging and querying.

**Tasks**:

1. Create DataForge client in VibeForge:
   - `lib/clients/dataforge_client.py`
   - Connection pooling
   - Retry logic with exponential backoff
   - Error handling and fallbacks

2. Add logging middleware:
   - Track all wizard interactions
   - Log language selections
   - Log stack choices (recommended vs chosen)
   - Capture user overrides

3. Create experience context service:
   - `services/experience_context.py`
   - Query similar projects from DataForge
   - Aggregate language preferences
   - Calculate stack success scores
   - Build context object for LLM prompts

4. Enhance stack recommendation endpoint:
   - Add `/api/v1/stacks/recommend-adaptive` endpoint
   - Include historical context in ranking
   - Return explainable recommendations with reasoning

**Deliverables**:

- DataForge client library
- Logging middleware active on all wizard endpoints
- Experience context service
- Enhanced recommendation endpoint with history

---

### Milestone 3.3: Frontend Learning Integration (2 days)

**Goal**: Display historical insights and learning-based recommendations in the UI.

**Tasks**:

1. Create new Svelte components:
   - `HistoricalInsights.svelte` - Show past project patterns
   - `AdaptiveRecommendation.svelte` - Display AI reasoning
   - `SuccessMetrics.svelte` - Stack performance charts

2. Update Step 2 (Languages):
   - Show "You frequently use: Python, TypeScript"
   - Display language recommendations based on history
   - Add "Why?" tooltips explaining reasoning

3. Update Step 3 (Stack Selection):
   - Add "Recommended based on your history" badge
   - Show success rate badges on stack cards
   - Display "Similar to your past project: X" hints

4. Update Step 5 (Review):
   - Add "Historical Performance" section
   - Show predicted success probability
   - Display "Projects like this succeeded with: ..."

**Deliverables**:

- 3 new UI components
- Updated wizard steps with historical context
- Interactive tooltips with explanations

---

### Milestone 3.4: Outcome Tracking & Feedback Loop (3 days)

**Goal**: Close the learning loop by tracking project outcomes and feeding back into recommendations.

**Tasks**:

1. Create project dashboard page:
   - `/projects/{id}/dashboard`
   - Build status tracking
   - Test pass/fail rates
   - Deployment status
   - User satisfaction rating

2. Add feedback collection:
   - Post-generation survey (1-5 stars)
   - "Was this stack helpful?" prompt
   - Issue tracking integration
   - Fix iteration counter

3. Build outcome aggregation pipeline:
   - Scheduled job to calculate stack success rates
   - Model performance aggregation
   - Language preference updates
   - Trend detection

4. Create admin analytics dashboard:
   - `/admin/analytics`
   - Stack performance over time
   - Language popularity trends
   - Model effectiveness comparison
   - User preference distributions

**Deliverables**:

- Project outcome tracking system
- Feedback collection UI
- Automated aggregation pipeline
- Analytics dashboard for system monitoring

---

### Milestone 3.5: Enhanced Stack Advisor (2-3 days)

**Goal**: Upgrade the LLM-powered Stack Advisor to use historical context.

**Tasks**:

1. Create enhanced prompt template:
   - Include `experience_context` in system prompt
   - Add user language history
   - Add similar project outcomes
   - Add stack success metrics

2. Implement scoring algorithm:

   ```python
   stack_score = (
       base_profile_score * 0.3 +
       language_match_bonus * 0.2 +
       historical_success * 0.25 +
       user_preference * 0.15 +
       project_type_match * 0.1
   )
   ```

3. Add explainability:
   - Generate reasoning for each recommendation
   - Reference specific past projects
   - Cite success rates
   - Explain language compatibility

4. Build confidence scoring:
   - Calculate confidence based on data volume
   - Show "High confidence" / "Limited data" badges
   - Recommend gathering more feedback when needed

**Deliverables**:

- Enhanced Stack Advisor with historical context
- Scoring algorithm implementation
- Explainable recommendations
- Confidence indicators

---

## Integration Points with Current System

### Phase 2 Wizard Modifications

**Step 1 (Project Intent)**:

- Log: project name, type, team size, timeline
- Query: similar projects by type

**Step 2 (Languages)**:

- Log: selected languages
- Query: user's most-used languages
- Display: "You often choose Python for AI projects"

**Step 3 (Stack Selection)**:

- Log: recommended stacks, chosen stack, override flag
- Query: stack success rates for selected languages
- Display: success rate badges, historical performance

**Step 4 (Configuration)**:

- Log: database choice, auth method, deployment platform
- Query: common configurations for chosen stack

**Step 5 (Review)**:

- Log: complete session data to DataForge
- Display: predicted success probability based on history

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VibeForge Frontend                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Wizard    │→ │  Learning  │→ │ Historical │            │
│  │  Steps     │  │  Insights  │  │  Context   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                  VibeForge Backend API                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Stack     │→ │ Experience │→ │  DataForge │            │
│  │  Advisor   │  │  Context   │  │   Client   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                     DataForge Database                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Projects  │  │  Sessions  │  │  Outcomes  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│  ┌────────────┐  ┌────────────┐                            │
│  │   Model    │  │  Language  │                            │
│  │Performance │  │Preferences │                            │
│  └────────────┘  └────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    NeuroForge Orchestrator                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Learning  │  │  Model     │  │ Adaptive   │            │
│  │  Engine    │  │  Router    │  │ Reasoning  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints Summary

### New DataForge Endpoints

**Projects**:

- `POST /api/projects` - Create project record
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `GET /api/projects?user_id={id}` - List user projects

**Sessions**:

- `POST /api/sessions` - Log wizard session
- `GET /api/sessions/{project_id}` - Get project sessions

**Outcomes**:

- `POST /api/outcomes` - Record build/test outcome
- `GET /api/outcomes/{project_id}` - Get project outcomes

**Analytics**:

- `GET /api/analytics/stack-success?stack={id}` - Stack success rate
- `GET /api/analytics/language-trends?user_id={id}` - Language usage
- `GET /api/analytics/preferences/{user_id}` - User preferences
- `GET /api/analytics/similar-projects?type={type}&languages={langs}`

### Enhanced VibeForge Endpoints

**Stack Advisor**:

- `POST /api/v1/stacks/recommend-adaptive` - Context-aware recommendations
  ```json
  {
    "project_type": "web",
    "languages": ["python", "typescript"],
    "user_id": "charles",
    "include_history": true
  }
  ```

**Experience Context**:

- `GET /api/v1/experience/context?user_id={id}&languages={langs}`
- Returns aggregated historical context for recommendations

---

## Database Schema Details

### `projects` Table

```sql
CREATE TABLE projects (
    project_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    project_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    languages TEXT[], -- PostgreSQL array
    stack_profile VARCHAR(100),
    priority_flags TEXT[],
    status VARCHAR(50) DEFAULT 'active',
    user_id VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_type ON projects(project_type);
CREATE INDEX idx_projects_stack ON projects(stack_profile);
CREATE INDEX idx_projects_languages ON projects USING GIN(languages);
```

### `project_sessions` Table

```sql
CREATE TABLE project_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    selected_languages TEXT[],
    suggested_stacks TEXT[],
    chosen_stack VARCHAR(100),
    user_overrode_suggestion BOOLEAN DEFAULT FALSE,
    configuration JSONB,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX idx_sessions_project ON project_sessions(project_id);
CREATE INDEX idx_sessions_timestamp ON project_sessions(timestamp);
```

### `stack_outcomes` Table

```sql
CREATE TABLE stack_outcomes (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    stack_profile VARCHAR(100) NOT NULL,
    languages TEXT[],
    period VARCHAR(20), -- e.g., "2025-Q4"
    build_success_rate DECIMAL(3,2),
    test_pass_rate DECIMAL(3,2),
    num_fix_iterations INTEGER,
    num_generated_scaffolds INTEGER,
    subjective_score DECIMAL(2,1),
    recorded_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX idx_outcomes_stack ON stack_outcomes(stack_profile);
CREATE INDEX idx_outcomes_period ON stack_outcomes(period);
CREATE INDEX idx_outcomes_languages ON stack_outcomes USING GIN(languages);
```

### `model_performance` Table

```sql
CREATE TABLE model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    language VARCHAR(50),
    framework VARCHAR(100),
    avg_fix_iterations DECIMAL(3,2),
    avg_user_rating DECIMAL(2,1),
    num_samples INTEGER,
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_perf_model ON model_performance(model_name);
CREATE INDEX idx_perf_language ON model_performance(language);
CREATE INDEX idx_perf_task ON model_performance(task_type);
```

### `language_preferences` Table

```sql
CREATE TABLE language_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    ranked_languages JSONB, -- [{language: "python", weight: 0.9}, ...]
    ranked_stacks JSONB,    -- [{stack_profile: "...", weight: 0.95}, ...]
    last_updated TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id)
);

CREATE INDEX idx_prefs_user ON language_preferences(user_id);
```

---

## Testing Strategy

### Unit Tests

- Service layer tests for each new service
- Model validation tests
- Scoring algorithm tests
- Client connection tests

### Integration Tests

- End-to-end wizard flow with logging
- DataForge query performance
- Experience context generation
- Recommendation enhancement

### Performance Tests

- Query optimization for historical lookups
- Index effectiveness
- API response times with large datasets
- Concurrent session handling

---

## Rollout Plan

### Phase 3A: Foundation (Week 1)

- Set up DataForge schema
- Create basic CRUD APIs
- Build DataForge client
- Add logging to wizard

### Phase 3B: Learning (Week 2)

- Implement experience context service
- Create enhanced recommendation endpoint
- Build frontend insights components
- Test adaptive recommendations

### Phase 3C: Feedback Loop (Week 3)

- Add outcome tracking
- Build aggregation pipeline
- Create analytics dashboard
- Implement confidence scoring

### Phase 3D: Optimization (Week 4)

- Performance tuning
- Index optimization
- Caching strategy
- Load testing

---

## Success Metrics

### Quantitative

- 90%+ of sessions logged to DataForge
- <100ms additional latency for context queries
- 95%+ test coverage on new code
- 10+ data points per stack for confidence

### Qualitative

- Users see relevant historical insights
- Recommendations feel more personalized
- "Why?" explanations are clear and helpful
- System improves over time visibly

---

## Future Enhancements (Phase 4+)

1. **Team/Org Learning**
   - Aggregate preferences across teams
   - Share successful patterns within orgs
   - Role-based recommendations

2. **Predictive Analytics**
   - Project success prediction
   - Estimated completion time
   - Resource requirements forecast
   - Risk assessment

3. **Model Routing Intelligence**
   - Automatic model selection per task
   - Cost optimization
   - Quality vs speed tradeoffs
   - Fallback strategies

4. **Real-time Adaptation**
   - Stream processing for live metrics
   - A/B testing framework
   - Dynamic scoring weights
   - Drift detection and alerts

5. **Cross-Project Insights**
   - "Projects using this stack also used..."
   - Technology adoption trends
   - Framework lifecycle tracking
   - Community patterns

---

## Dependencies

### Technology Stack

- **DataForge**: PostgreSQL 14+ with JSONB
- **VibeForge Backend**: FastAPI with async support
- **VibeForge Frontend**: SvelteKit with charts library
- **Caching**: Redis for hot data
- **Monitoring**: Prometheus + Grafana

### External Services

- LLM APIs (OpenAI, Anthropic) - already integrated
- Optional: Analytics platform for deeper insights

---

## Risks & Mitigations

**Risk**: Cold start problem (no historical data initially)

- **Mitigation**: Use rule-based fallbacks, gradually transition to ML

**Risk**: Privacy concerns with user data

- **Mitigation**: Anonymization options, user consent, data retention policies

**Risk**: Performance degradation with large datasets

- **Mitigation**: Proper indexing, query optimization, pagination, caching

**Risk**: Recommendation bias towards popular choices

- **Mitigation**: Diversity scoring, exploration vs exploitation balance

---

## Alignment with NeuroForge Vision

This phase directly implements the **NeuroForge Learning Layer** blueprint:

- ✅ Long-term memory via DataForge
- ✅ Adaptive reasoning via experience context
- ✅ Explainable recommendations
- ✅ Continuous improvement loop
- ✅ No model retraining required
- ✅ Lightweight, practical approach

**NeuroForge becomes the brain, DataForge becomes the memory, VibeForge becomes the interface.**

---

## End of Phase 3 Plan

**Status**: Ready to begin after Phase 2 completion  
**Estimated Duration**: 3-4 weeks  
**Team Size**: 2-3 developers  
**Priority**: High (enables core differentiation)
