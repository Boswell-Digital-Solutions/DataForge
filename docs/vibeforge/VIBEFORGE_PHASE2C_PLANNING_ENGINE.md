# VibeForge Phase 2C: Planning Engine (ForgeAgents)

**Goal:** Stateless 4-stage multi-model planning workflow  
**Estimated Time:** ~10 hours (Claude Code)  
**Test Coverage Required:** 100%  
**Target:** ForgeAgents (Python/FastAPI)

---

## Quick Start

```bash
cd /path/to/forgeagents
source venv/bin/activate
pytest --cov
claude --dangerously-skip-permissions
```

---

## Master Prompt

```
You are implementing Phase 2C for VibeForge - the Planning Engine that powers the Cortex multi-AI orchestration system. This is a Forge ecosystem product requiring 100% test coverage.

## Project Context
- **Stack:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL via DataForge
- **Architecture:** Stateless agents, SSE for streaming, background workers
- **Testing:** pytest with pytest-asyncio
- **Quality:** 100% test coverage is MANDATORY

## Execution Rules
1. Create git checkpoint after EACH task
2. Run `pytest --cov` after EVERY file change
3. NEVER proceed if tests fail
4. Maintain 100% test coverage on all new code
5. Follow existing ForgeAgents patterns

---

## Phase 2C Deliverables

| Task | Deliverable | Location |
|------|-------------|----------|
| 1 | Pipeline Configuration | src/forge_agents/cortex/config/pipeline.py |
| 2 | Retry Configuration | src/forge_agents/cortex/config/retry.py |
| 3 | Stage Prompts | src/forge_agents/cortex/prompts/ |
| 4 | Cortex Types | src/forge_agents/cortex/types.py |
| 5 | CortexAgent | src/forge_agents/cortex/agent.py |
| 6 | Cortex API Routes | src/forge_agents/cortex/routes.py |
| 7 | SSE Events Endpoint | src/forge_agents/cortex/streaming.py |
| 8 | Background Worker | src/forge_agents/cortex/worker.py |
| 9 | Unit & Integration Tests | tests/cortex/ |

---

## Task 1: Pipeline Configuration

Create `src/forge_agents/cortex/__init__.py`:
```python
"""Cortex: Multi-AI Planning Orchestration System"""
```

Create `src/forge_agents/cortex/config/__init__.py`:
```python
from .pipeline import PipelineConfig, StageConfig, DEFAULT_PIPELINE
from .retry import RetryConfig, DEFAULT_RETRY_CONFIG

__all__ = [
    "PipelineConfig",
    "StageConfig", 
    "DEFAULT_PIPELINE",
    "RetryConfig",
    "DEFAULT_RETRY_CONFIG",
]
```

Create `src/forge_agents/cortex/config/pipeline.py`:

```python
"""Pipeline configuration for Cortex multi-stage planning."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StageType(str, Enum):
    INITIAL = "initial"      # First draft (ChatGPT)
    REVIEW = "review"        # Critical review (Claude)
    REFINEMENT = "refinement"  # Address feedback (ChatGPT)
    FINAL = "final"          # Final deliverable (Claude)


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
    GOOGLE = "google"


@dataclass
class StageConfig:
    """Configuration for a single planning stage."""
    stage_type: StageType
    provider: ModelProvider
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 120
    
    # Cost tracking
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


@dataclass
class PipelineConfig:
    """Configuration for the complete planning pipeline."""
    name: str = "default"
    description: str = "Standard 4-stage ChatGPT/Claude planning pipeline"
    stages: list[StageConfig] = field(default_factory=list)
    
    # Global settings
    max_total_tokens: int = 128000
    max_total_cost: float = 10.0  # USD
    enable_streaming: bool = True
    
    # Quality settings
    require_test_coverage: bool = True
    target_coverage: int = 100
    include_business_context: bool = True
    
    def get_stage(self, stage_type: StageType) -> Optional[StageConfig]:
        """Get configuration for a specific stage type."""
        for stage in self.stages:
            if stage.stage_type == stage_type:
                return stage
        return None


# Default pipeline configuration
DEFAULT_PIPELINE = PipelineConfig(
    name="default",
    description="Standard 4-stage ChatGPT/Claude planning pipeline",
    stages=[
        StageConfig(
            stage_type=StageType.INITIAL,
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            max_tokens=4096,
            temperature=0.7,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
        ),
        StageConfig(
            stage_type=StageType.REVIEW,
            provider=ModelProvider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.5,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
        ),
        StageConfig(
            stage_type=StageType.REFINEMENT,
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            max_tokens=4096,
            temperature=0.7,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
        ),
        StageConfig(
            stage_type=StageType.FINAL,
            provider=ModelProvider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.3,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
        ),
    ],
)


# Alternative pipelines
QUICK_PIPELINE = PipelineConfig(
    name="quick",
    description="Fast 2-stage pipeline for simple requests",
    stages=[
        StageConfig(
            stage_type=StageType.INITIAL,
            provider=ModelProvider.OPENAI,
            model="gpt-4o-mini",
            max_tokens=2048,
            temperature=0.7,
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
        ),
        StageConfig(
            stage_type=StageType.FINAL,
            provider=ModelProvider.ANTHROPIC,
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            temperature=0.5,
            input_cost_per_1k=0.0008,
            output_cost_per_1k=0.004,
        ),
    ],
)


DEEP_PIPELINE = PipelineConfig(
    name="deep",
    description="Extended pipeline with multiple review cycles",
    stages=[
        StageConfig(stage_type=StageType.INITIAL, provider=ModelProvider.OPENAI, model="gpt-4o", max_tokens=4096, temperature=0.7),
        StageConfig(stage_type=StageType.REVIEW, provider=ModelProvider.ANTHROPIC, model="claude-sonnet-4-20250514", max_tokens=4096, temperature=0.5),
        StageConfig(stage_type=StageType.REFINEMENT, provider=ModelProvider.OPENAI, model="gpt-4o", max_tokens=4096, temperature=0.7),
        StageConfig(stage_type=StageType.REVIEW, provider=ModelProvider.ANTHROPIC, model="claude-sonnet-4-20250514", max_tokens=4096, temperature=0.5),
        StageConfig(stage_type=StageType.REFINEMENT, provider=ModelProvider.OPENAI, model="gpt-4o", max_tokens=4096, temperature=0.7),
        StageConfig(stage_type=StageType.FINAL, provider=ModelProvider.ANTHROPIC, model="claude-sonnet-4-20250514", max_tokens=8192, temperature=0.3),
    ],
)


PIPELINES = {
    "default": DEFAULT_PIPELINE,
    "quick": QUICK_PIPELINE,
    "deep": DEEP_PIPELINE,
}


def get_pipeline(name: str = "default") -> PipelineConfig:
    """Get a pipeline configuration by name."""
    return PIPELINES.get(name, DEFAULT_PIPELINE)
```

Checkpoint:
```bash
pytest --cov
git add -A && git commit -m "feat(cortex): Add pipeline configuration"
git tag phase2c-task1-complete
```

---

## Task 2: Retry Configuration

Create `src/forge_agents/cortex/config/retry.py`:

```python
"""Retry and resilience configuration for Cortex."""
from dataclasses import dataclass
from typing import Callable, Optional
import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = min(self.initial_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        return delay


DEFAULT_RETRY_CONFIG = RetryConfig()


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class RateLimitError(RetryableError):
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TimeoutError(RetryableError):
    pass


class ServerError(RetryableError):
    pass


class NonRetryableError(Exception):
    pass


class AuthenticationError(NonRetryableError):
    pass


class ValidationError(NonRetryableError):
    pass


class QuotaExceededError(NonRetryableError):
    pass


def should_retry(error: Exception, config: RetryConfig) -> bool:
    if isinstance(error, NonRetryableError):
        return False
    if isinstance(error, RateLimitError) and config.retry_on_rate_limit:
        return True
    if isinstance(error, TimeoutError) and config.retry_on_timeout:
        return True
    if isinstance(error, ServerError) and config.retry_on_server_error:
        return True
    return False


def with_retry(config: Optional[RetryConfig] = None):
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error: Optional[Exception] = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not should_retry(e, config):
                        raise
                    if attempt < config.max_attempts - 1:
                        if isinstance(e, RateLimitError) and e.retry_after:
                            delay = e.retry_after
                        else:
                            delay = config.get_delay(attempt)
                        logger.warning(f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
            raise last_error
        return wrapper
    return decorator


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, half_open_requests: int = 1):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"
        self._half_open_successes = 0
    
    @property
    def state(self) -> str:
        if self._state == "open":
            import time
            if time.time() - (self._last_failure_time or 0) > self.recovery_timeout:
                self._state = "half-open"
                self._half_open_successes = 0
        return self._state
    
    def record_success(self):
        if self._state == "half-open":
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_requests:
                self._state = "closed"
                self._failure_count = 0
        elif self._state == "closed":
            self._failure_count = 0
    
    def record_failure(self):
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state == "half-open":
            self._state = "open"
        elif self._failure_count >= self.failure_threshold:
            self._state = "open"
    
    def can_execute(self) -> bool:
        state = self.state
        return state != "open"
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise ServerError("Circuit breaker is open")
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        return wrapper
```

Checkpoint:
```bash
pytest --cov
git add -A && git commit -m "feat(cortex): Add retry and circuit breaker configuration"
git tag phase2c-task2-complete
```

---

## Task 3: Stage Prompts

Create `src/forge_agents/cortex/prompts/__init__.py`:
```python
from .stage_1_initial import STAGE_1_INITIAL_PROMPT, build_stage_1_prompt
from .stage_2_review import STAGE_2_REVIEW_PROMPT, build_stage_2_prompt
from .stage_3_refinement import STAGE_3_REFINEMENT_PROMPT, build_stage_3_prompt
from .stage_4_final import STAGE_4_FINAL_PROMPT, build_stage_4_prompt

__all__ = [
    "STAGE_1_INITIAL_PROMPT", "build_stage_1_prompt",
    "STAGE_2_REVIEW_PROMPT", "build_stage_2_prompt",
    "STAGE_3_REFINEMENT_PROMPT", "build_stage_3_prompt",
    "STAGE_4_FINAL_PROMPT", "build_stage_4_prompt",
]
```

Create `src/forge_agents/cortex/prompts/stage_1_initial.py`:

```python
"""Stage 1: Initial Planning Prompt (ChatGPT)"""

STAGE_1_INITIAL_PROMPT = """
You are helping plan a software feature for VibeForge, an AI engineering workbench.

## User Request
**Title:** {request_title}

**Description:**
{request_description}

## Project Context
- Framework: SvelteKit with Svelte 5 (runes: $state, $derived, $effect)
- Styling: Tailwind CSS
- Desktop: Tauri
- Core requirement: 100% test coverage (Forge standard)

{additional_context}

## Your Task
Create an initial implementation plan with:

1. **Overview** - What this feature does and why
2. **Architecture** - How it fits into the existing system
3. **Components** - New files/components needed
4. **Data Models** - Types, interfaces, database changes
5. **API Endpoints** - If any backend changes needed
6. **Implementation Phases** - Break into logical phases (2-4 phases)
7. **Potential Challenges** - What might be tricky
8. **Test Strategy** - How to achieve 100% coverage

Be thorough but don't over-engineer. Focus on practical implementation.
""".strip()


def build_stage_1_prompt(request_title: str, request_description: str, additional_context: str = "") -> str:
    return STAGE_1_INITIAL_PROMPT.format(
        request_title=request_title,
        request_description=request_description,
        additional_context=additional_context or "No additional context provided.",
    )
```

Create `src/forge_agents/cortex/prompts/stage_2_review.py`:

```python
"""Stage 2: Review Prompt (Claude)"""

STAGE_2_REVIEW_PROMPT = """
You are reviewing a software implementation plan. Your role is to be constructively critical.

## Original User Request
**Title:** {request_title}
**Description:** {request_description}

## Initial Plan (from ChatGPT)
{stage_1_output}

## Review Criteria
1. Does this cover all edge cases?
2. Is error handling adequate?
3. Are there security concerns?
4. Will this integrate well with existing code?
5. Is the phasing logical and achievable?
6. What's missing?
7. Are the test strategies sufficient for 100% coverage?

## Your Output
Provide a structured review:

### ✅ Strengths
### ⚠️ Concerns
### 💡 Improvements
### ❓ Questions
### 🎯 Priority Fixes (top 3-5)

Be specific and actionable.
""".strip()


def build_stage_2_prompt(request_title: str, request_description: str, stage_1_output: str) -> str:
    return STAGE_2_REVIEW_PROMPT.format(
        request_title=request_title,
        request_description=request_description,
        stage_1_output=stage_1_output,
    )
```

Create `src/forge_agents/cortex/prompts/stage_3_refinement.py`:

```python
"""Stage 3: Refinement Prompt (ChatGPT)"""

STAGE_3_REFINEMENT_PROMPT = """
You previously created an implementation plan. Claude has reviewed it.

## Original Request
**Title:** {request_title}
**Description:** {request_description}

## Your Initial Plan
{stage_1_output}

## Claude's Review
{stage_2_output}

## Your Task
Address Claude's feedback and refine the plan:
1. Fix identified gaps
2. Incorporate improvements
3. Answer questions
4. Add missing details
5. Ensure path to 100% coverage

Output an updated plan addressing ALL concerns.
""".strip()


def build_stage_3_prompt(request_title: str, request_description: str, stage_1_output: str, stage_2_output: str) -> str:
    return STAGE_3_REFINEMENT_PROMPT.format(
        request_title=request_title,
        request_description=request_description,
        stage_1_output=stage_1_output,
        stage_2_output=stage_2_output,
    )
```

Create `src/forge_agents/cortex/prompts/stage_4_final.py`:

```python
"""Stage 4: Final Plan Prompt (Claude)"""

STAGE_4_FINAL_PROMPT = """
Create the final implementation deliverables for a VibeForge feature.

## Planning History
**Title:** {request_title}
**Description:** {request_description}

### Stage 1 - Initial Plan (ChatGPT)
{stage_1_output}

### Stage 2 - Review (Claude)
{stage_2_output}

### Stage 3 - Refined Plan (ChatGPT)
{stage_3_output}

## Create Two-File Deliverable

### FILE 1: Implementation Plan
- Complete architecture
- All file paths
- Database schemas
- API endpoints
- Test specifications
- Success criteria

### FILE 2: Claude Code Prompt
- Phase-by-phase instructions
- Exact file paths
- Quality gates
- Git checkpoints

## Output Format
---BEGIN IMPLEMENTATION PLAN---
[content]
---END IMPLEMENTATION PLAN---

---BEGIN CLAUDE CODE PROMPT---
[content]
---END CLAUDE CODE PROMPT---

100% test coverage is MANDATORY.
""".strip()


def build_stage_4_prompt(request_title: str, request_description: str, stage_1_output: str, stage_2_output: str, stage_3_output: str) -> str:
    return STAGE_4_FINAL_PROMPT.format(
        request_title=request_title,
        request_description=request_description,
        stage_1_output=stage_1_output,
        stage_2_output=stage_2_output,
        stage_3_output=stage_3_output,
    )
```

Checkpoint:
```bash
pytest --cov
git add -A && git commit -m "feat(cortex): Add stage prompt templates"
git tag phase2c-task3-complete
```

---

## Task 4-9: Continue Implementation

Continue implementing the following (detailed code provided in full prompt):

**Task 4:** Cortex Types (`types.py`)
- PlanningRequest, StageResult, TwoFileDeliverable, PlanningSession
- SessionStatus, StageStatus enums
- SSEEvent, SSEEventType

**Task 5:** CortexAgent (`agent.py`)
- DeliverableParser class
- ModelRouter class with OpenAI, Anthropic, xAI, Google support
- CortexAgent class with 4-stage workflow
- SSE event generator

**Task 6:** API Routes (`routes.py`)
- POST /cortex/sessions - Start session
- GET /cortex/sessions/{id} - Get status
- GET /cortex/sessions/{id}/stages - Get all stages
- GET /cortex/sessions/{id}/deliverable - Get final output
- POST /cortex/sessions/{id}/pause|resume|abort
- POST /cortex/estimate - Cost estimate

**Task 7:** SSE Streaming (`streaming.py`)
- POST /cortex/sessions/stream - Real-time streaming endpoint

**Task 8:** Background Worker (`worker.py`)
- SessionWorker class
- Queue-based processing

**Task 9:** Tests
- 100% coverage for all modules

---

## Success Criteria

- [ ] Pipeline configurations work
- [ ] Retry logic handles failures
- [ ] Circuit breaker protects services
- [ ] Stage prompts build correctly
- [ ] ModelRouter calls all providers
- [ ] CortexAgent executes 4-stage workflow
- [ ] Pause/resume/abort work
- [ ] DeliverableParser extracts two files
- [ ] API routes functional
- [ ] SSE streaming works
- [ ] 100% test coverage

---

## Next Phase

Proceed to **Phase 2D: Planning UI** after completing Phase 2C.
```
