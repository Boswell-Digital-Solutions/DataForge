# NeuroForge Psychology Implementation Context
**Complete End-to-End System Architecture**

**Status:** Ready for Implementation  
**Target Duration:** 9-14 weeks  
**Scope:** Phases 0-5 (Complete)

---

## EXECUTIVE SUMMARY

Build a psychology-grounded user understanding system across the Forge Ecosystem. System learns how users think, work, and create — then applies that understanding across all ecosystem apps to deliver personalized, proactive assistance.

**Core Principle:** User success = Our success. Measure everything against: Are they better writers/engineers/creators?

---

## ECOSYSTEM ARCHITECTURE

### Services & Ports

```
AuthorForge/VibeForge (Consumer Apps)
    ↓
ForgeAgents:8787 (Agent Orchestration)
    ├→ NeuroForge:8000 (AI Reasoning)
    ├→ DataForge:8788 (Persistent Memory + Learning)
    └→ Rake:8002 (Data Ingestion)
```

### Service Responsibilities for Psychology System

| Service | Role | Owns |
|---------|------|------|
| **NeuroForge** | Psychological reasoning engine | Frameworks, LLM reasoning, inference models |
| **ForgeAgents** | Agent orchestration | Profiling agents, lifecycle management, policy enforcement |
| **DataForge** | Persistent memory + learning | Signal storage, profile storage, feedback collection, EMA scoring |
| **Rake** | Data ingestion pipeline | Behavioral signal ingestion from apps |

---

## IMPLEMENTATION PHASES

### PHASE 0-1: NeuroForge Psychology Engine (4-6 weeks)
**Deliverable:** `psychological_reasoner` model accessible via `/api/v1/infer`

**Frameworks to Implement:**
1. Big 5 Personality (OCEAN) - trait inference
2. Self-Determination Theory - motivation profiling
3. Learning Modalities - visual/auditory/kinesthetic/reading
4. Decision Styles - maximizer vs satisficer, analytical vs intuitive
5. Flow Theory - window detection and optimization
6. Growth vs Fixed Mindset - confidence and learning orientation
7. Cognitive Load Theory - current capacity estimation
8. Behavioral Economics - bias detection (loss aversion, overconfidence)
9. Habit Formation - pattern recognition

**Code Structure:**
```
NeuroForge/neuroforge_backend/
├── psychology/
│   ├── __init__.py
│   ├── frameworks/
│   │   ├── big_five.py
│   │   ├── motivation.py
│   │   ├── learning_styles.py
│   │   ├── decision_styles.py
│   │   ├── flow.py
│   │   ├── growth_mindset.py
│   │   ├── cognitive_load.py
│   │   ├── biases.py
│   │   └── habits.py
│   ├── inference/
│   │   ├── signal_processor.py (signals → traits)
│   │   ├── profile_builder.py (traits → profile)
│   │   └── confidence_calculator.py
│   └── models/
│       └── psychological_profile.py (data models)
├── routers/
│   └── psychology.py (POST /api/v1/infer endpoint)
└── tests/
    └── psychology/
```

**API Contract:**
```python
POST /api/v1/infer
Request:
{
    "model": "psychological_reasoner",
    "input": {
        "behavioral_signals": [
            {
                "action_type": "chose_model",
                "action_value": "claude-opus",
                "context": "high_quality_task",
                "outcome_rating": 4.5,
                "timestamp": "2025-12-11T10:30:00Z"
            },
            ...
        ]
    }
}

Response:
{
    "profile": {
        "personality": {
            "openness": 0.65,
            "conscientiousness": 0.85,
            "extraversion": 0.45,
            "agreeableness": 0.70,
            "neuroticism": 0.35,
            "confidence": 0.82
        },
        "motivation": {
            "autonomy": 0.70,
            "competence": 0.85,
            "relatedness": 0.55,
            "confidence": 0.78
        },
        "learning_style": {
            "visual": 0.60,
            "auditory": 0.30,
            "kinesthetic": 0.80,
            "reading_writing": 0.50,
            "preference": "kinesthetic",
            "confidence": 0.75
        },
        "decision_style": {
            "maximizer_satisficer": 0.7,  # 1=maximizer, 0=satisficer
            "analytical_intuitive": 0.6,
            "quick_deliberative": 0.4,
            "risk_tolerance": 0.6,
            "confidence": 0.72
        },
        "flow_patterns": {
            "optimal_duration_minutes": 90,
            "peak_hours": ["10:00-12:00", "14:00-16:00"],
            "blockers": ["perfectionism", "fear_of_judgment"],
            "enablers": ["autonomy", "clear_goals"],
            "confidence": 0.68
        },
        "growth_mindset": 0.75,
        "confidence_level": 4.2,
        "cognitive_load": {
            "current": 0.6,  # 0-1 scale
            "decision_complexity_tolerance": 0.8
        }
    },
    "overall_confidence": 0.76,
    "profile_version": "1.0",
    "generated_at": "2025-12-11T10:35:00Z"
}
```

---

### PHASE 2: ForgeAgents Psychology Agents (2-3 weeks)
**Deliverable:** 6 psychology-aware agents using ForgeAgents framework

**Agents to Implement:**

1. **ProfileBuilderAgent**
   - Orchestrates profile building
   - Queries DataForge for signals
   - Calls NeuroForge for reasoning
   - Stores profile in DataForge
   - Collects user feedback

2. **ContextSelectionAgent**
   - Uses profile to select context
   - Visual learners get visual examples
   - Kinesthetic learners get working examples
   - Respects learning style preferences

3. **RoutingAgent**
   - Uses profile to select model
   - High conscientiousness → quality over cost
   - Risk-averse → proven models
   - Maximizers → full explanation

4. **FlowEnablerAgent**
   - Detects flow state
   - Protects flow windows
   - Pre-stages resources
   - Messages: "You're in the zone. Keep going."

5. **BlockerBreakerAgent**
   - Detects: perfectionism, analysis paralysis, fear, imposter syndrome
   - Intervenes with psychology-aware messaging
   - Helps users get unstuck

6. **ConfidenceBuilderAgent**
   - Detects low confidence
   - Gathers evidence of mastery
   - Frames based on learning style
   - Builds trust in system

**Code Structure:**
```
ForgeAgents/app/agents/
├── reference/
│   ├── psychology_aware.py (base for psychology agents)
│   ├── profile_builder_agent.py (600 lines)
│   ├── context_selection_agent.py (500 lines)
│   ├── routing_agent.py (500 lines)
│   ├── flow_enabler_agent.py (400 lines)
│   ├── blocker_breaker_agent.py (450 lines)
│   └── confidence_builder_agent.py (400 lines)
└── tests/
    └── test_psychology_agents.py
```

---

### PHASE 3: DataForge Profile Learning (1-2 weeks)
**Deliverable:** Profile learning and EMA scoring

**Changes to DataForge:**

1. **Extend planning_outcomes table:**
   ```python
   class PlanningOutcome(Base):
       # ... existing fields ...
       
       # NEW: Psychology-specific fields
       psychological_profile: JSON  # Inferred profile
       agent_decisions: JSON         # Which agents decided
       behavioral_signals: JSON      # Signals used
       signal_embeddings: Vector[]   # For semantic search
   ```

2. **New DataForge endpoints:**
   ```
   GET /api/v1/learning/psychological-profile/{user_id}
   GET /api/v1/learning/profile-accuracy/{user_id}
   GET /api/v1/learning/profile-evolution/{user_id}?days=30
   ```

3. **Profile accuracy EMA tracking:**
   ```python
   profile_accuracy_ema = calculate_ema(
       previous_ema=0.72,
       new_value=5.0,  # user rating
       alpha=0.3
   )
   # Result: How accurate is profile prediction?
   ```

**Database Schema Changes:**
```sql
-- Extend planning_outcomes
ALTER TABLE planning_outcomes
ADD COLUMN psychological_profile JSONB,
ADD COLUMN agent_decisions JSONB,
ADD COLUMN behavioral_signals JSONB,
ADD COLUMN signal_embedding VECTOR(1536);

-- New table: psychological_profiles (denormalized for fast lookup)
CREATE TABLE psychological_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE,
    profile JSONB NOT NULL,
    confidence FLOAT NOT NULL,
    profile_version INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    feedback_count INT DEFAULT 0,
    accuracy_ema FLOAT DEFAULT 0.5
);

-- Index for fast user lookup
CREATE INDEX idx_psychological_profiles_user_id 
ON psychological_profiles(user_id);
```

---

### PHASE 4: Behavioral Signal Ingestion (1-2 weeks)
**Deliverable:** Rake ingestion of behavioral signals

**New Rake Source Type:** `behavioral_signal`

**Signal Schema:**
```python
class BehavioralSignal(BaseModel):
    user_id: str
    action_type: str  # chose_model, abandoned_project, revised_count, etc.
    action_value: Any  # claude-opus, 5_revisions, etc.
    context: str  # task type, time of day, etc.
    outcome_rating: float  # 0-5 user satisfaction
    timestamp: datetime
    duration_ms: float
    session_length_min: int
    metadata: Dict[str, Any]  # Custom fields
```

**Rake Pipeline for Signals:**
1. FETCH: Get signal from AuthorForge/VibeForge
2. CLEAN: Normalize and validate
3. CHUNK: One signal = one chunk
4. EMBED: Generate embedding for semantic search
5. STORE: Send to DataForge

**Code Structure:**
```
Rake/
├── sources/
│   └── behavioral_signal.py (200 lines)
├── pipeline/
│   └── [existing 5-stage pipeline, no changes needed]
└── tests/
    └── test_behavioral_signal_source.py
```

**Integration Point (AuthorForge/VibeForge):**
```python
# When user takes action, emit signal
await emit_behavioral_signal(
    user_id=current_user.id,
    action_type="chose_model",
    action_value="claude-opus",
    context="high_quality_task",
    outcome_rating=user_satisfaction,
    timestamp=now()
)

# This calls Rake:
POST http://localhost:8002/api/v1/jobs
{
    "source": "behavioral_signal",
    "signal": {...}
}
```

---

### PHASE 5: Cross-App Integration (1 week)
**Deliverable:** Profiles shared across ecosystem apps

**How It Works:**
1. Jane uses AuthorForge
   - System learns: visual examples, high conscientiousness, flow at 10-11am
   - Profile stored in DataForge

2. Jane uses VibeForge (new app)
   - ForgeAgents loads her profile from DataForge
   - Applies same understanding
   - Better defaults on day 1

3. Jane uses CodeForge (future)
   - Same profile, same insights
   - System already knows her patterns
   - Moat gets stronger (harder to copy)

**Network Effects:**
- App 1 (AuthorForge): Learn Jane's profile (3 months)
- App 2 (VibeForge): Get Jane's profile instantly, learn her coding style (1 month)
- App 3 (CodeForge): Get both profiles instantly, compound learning (1 week)

---

## DATA MODELS

### BehavioralSignal
```python
class BehavioralSignal(BaseModel):
    user_id: str
    action_type: str
    action_value: Any
    context: str
    outcome_rating: float
    timestamp: datetime
    duration_ms: float
    session_length_min: int
    metadata: Dict[str, Any] = {}
```

### PsychologicalProfile
```python
class PsychologicalProfile(BaseModel):
    user_id: str
    personality: {
        openness: float,
        conscientiousness: float,
        extraversion: float,
        agreeableness: float,
        neuroticism: float,
        confidence: float
    }
    motivation: {
        autonomy: float,
        competence: float,
        relatedness: float,
        confidence: float
    }
    learning_style: {
        visual: float,
        auditory: float,
        kinesthetic: float,
        reading_writing: float,
        preference: str,
        confidence: float
    }
    decision_style: {
        maximizer_satisficer: float,
        analytical_intuitive: float,
        quick_deliberative: float,
        risk_tolerance: float,
        confidence: float
    }
    flow_patterns: {
        optimal_duration_minutes: int,
        peak_hours: List[str],
        blockers: List[str],
        enablers: List[str],
        confidence: float
    }
    growth_mindset: float
    confidence_level: float
    cognitive_load: {
        current: float,
        decision_complexity_tolerance: float
    }
    overall_confidence: float
    profile_version: str
    generated_at: datetime
```

### AgentDecision
```python
class AgentDecision(BaseModel):
    agent_type: str  # profile_builder, context_selection, routing, etc.
    decision: str
    reasoning: str
    confidence: float
    impact_on_outcome: str
```

---

## CRITICAL SUCCESS METRICS

### TIER 1: User Success (Must-Have)
- Output quality improvement: +30% by day 90
- Confidence trajectory: +3 points by day 90
- Project completion rate: +30% by day 90
- Skill progression: 1 level every 3-4 months

### TIER 2: Behavioral Changes
- Flow state frequency: +150% by day 90
- Decision quality: +20% faster, same/better quality
- Risk-taking: More experimentation
- Feedback integration: >70% suggestion adoption

### TIER 3: Technical Validation
- Profile accuracy: >0.85 correlation vs self-report
- Behavioral prediction accuracy: >80% by week 4
- Profile stability: <5% weekly change after week 4

### TIER 4: System Validation
- Each agent success rate: >70%
- Full pipeline: <5s latency
- Agent interaction effects: Synergy bonus observed

### TIER 5: Trust & Transparency
- Profile transparency: >60% of users view profile
- Cross-app data sharing opt-in: >60%
- NPS (would recommend): >50

### TIER 6: Network Effects
- Cross-user pattern learning: 20% day-1 benefit by month 6
- Cross-app knowledge transfer: >30% day-1 improvement
- Learning velocity: +5-8% accuracy per month

### TIER 7: Market
- Competitive comparison: +20% better than ChatGPT
- Willingness to pay: >$25/month by month 6
- Retention: >60% at month 3, >50% at month 6

---

## REFACTORING REQUIRED

### NeuroForge
- Add `psychology/` module
- New router: `/api/v1/infer` for psychological_reasoner
- Type safety with Pydantic models
- Comprehensive error handling

### ForgeAgents
- Add 6 new agent implementations
- Base class: `PsychologyAwareAgent`
- Inherit all lifecycle/policy/memory/tool features
- No duplicate functionality

### DataForge
- Extend schema for profiles + signals
- New endpoints for profile management
- EMA calculation for accuracy tracking
- No breaking changes to existing APIs

### Rake
- New source type: `behavioral_signal`
- Reuse existing 5-stage pipeline
- No changes to core architecture

---

## CODE STANDARDS

**Type Safety:**
- 100% type hints
- Pydantic v2 for validation
- mypy strict mode

**Error Handling:**
- Custom exception hierarchy
- Detailed error messages
- Correlation ID tracking

**Testing:**
- Unit tests: frameworks, inference
- Integration tests: end-to-end flows
- Target: 80%+ coverage

**Documentation:**
- Docstrings: Google style
- README: 200+ lines
- API docs: OpenAPI 3.0

**Performance:**
- Latency targets: <100ms per inference
- Memory efficient: Streaming for large batches
- Async-first design

---

## IMPLEMENTATION CHECKLIST

### Phase 0-1: NeuroForge
- [ ] Implement Big 5 framework
- [ ] Implement motivation framework
- [ ] Implement learning styles framework
- [ ] Implement decision styles framework
- [ ] Implement flow theory framework
- [ ] Implement other frameworks
- [ ] Build signal processor (signals → traits)
- [ ] Build profile builder (traits → profile)
- [ ] Calculate confidence scores
- [ ] Create Pydantic models
- [ ] Write `/api/v1/infer` endpoint
- [ ] Comprehensive tests
- [ ] Documentation

### Phase 2: ForgeAgents
- [ ] Create base `PsychologyAwareAgent` class
- [ ] ProfileBuilderAgent
- [ ] ContextSelectionAgent
- [ ] RoutingAgent
- [ ] FlowEnablerAgent
- [ ] BlockerBreakerAgent
- [ ] ConfidenceBuilderAgent
- [ ] Integration tests
- [ ] Documentation

### Phase 3: DataForge
- [ ] Schema changes for profiles
- [ ] Schema changes for signals
- [ ] New psychological_profiles table
- [ ] EMA calculation logic
- [ ] New API endpoints
- [ ] Migration scripts
- [ ] Tests
- [ ] Documentation

### Phase 4: Rake
- [ ] New source type: behavioral_signal
- [ ] Signal validation
- [ ] Integration tests
- [ ] Documentation

### Phase 5: Integration
- [ ] Cross-app profile sharing
- [ ] Network effects validation
- [ ] E2E tests
- [ ] Documentation

---

## ASSUMPTIONS & CONSTRAINTS

**Assumptions:**
- Behavioral signals are reliable proxy for traits
- LLM reasoning can infer psychology accurately
- Users want personalization (not creepy)
- Cross-app learning is valuable

**Constraints:**
- All data must be encrypted in flight and at rest
- GDPR/CCPA compliance required
- Users must control their profiles
- No external analytics services
- Profiles are user-owned property

**Risks:**
- Inference accuracy <0.75 (validate early)
- Users reject psychological profiling (communicate transparently)
- Creepiness factor (emphasize control + transparency)
- Cold start problem (survey on day 1 to seed profile)

---

## SUCCESS CRITERIA

**Phase 0-1:** psychological_reasoner works, >0.75 accuracy on test set
**Phase 2:** 6 agents integrate with ForgeAgents, all tests pass
**Phase 3:** Profile learning in DataForge, EMA tracking works
**Phase 4:** Signals flow Rake → DataForge reliably
**Phase 5:** Cross-app integration works, network effects observed

**Overall:** By week 14, system helps users succeed measurably across entire ecosystem

---

## FINAL NOTES

**This is a real system.**
- Not theoretical
- Not a prototype
- Production-grade architecture
- Measurable outcomes

**Start with validation.**
- Phase 0-1: Can we infer psychology accurately?
- If >0.85 correlation to self-report → proceed boldly
- If <0.75 correlation → iterate on frameworks

**Build incrementally.**
- Each phase adds value
- Can stop and ship at any phase
- But full system is the vision

**The moat is real.**
- Competitors can copy features
- Competitors can't copy "understands how I work"
- And it gets better every day (learning)

Go build it.

