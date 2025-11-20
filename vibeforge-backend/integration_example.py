"""
Integration Example: Using vibeforge_prompt in FastAPI Routers

This file shows real-world usage of the Rust extension module
in a VibeForge FastAPI application.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

# ============================================================================
# IMPORTS FROM RUST EXTENSION
# ============================================================================
# These are the main imports from the compiled Rust module:

from vibeforge_prompt import (
    build_prompt,                      # Combine contexts into full prompt
    estimate_tokens,                   # Quick token estimation
    estimate_tokens_precise,           # Accurate token estimation  
    build_initial_run,                 # Create run record JSON
    estimate_tokens_for_prompt,        # Estimate tokens for built prompt
    PromptContext,                     # Stateful context management
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CreateRunRequest(BaseModel):
    """Request to create a new model run."""
    workspace_id: str
    model: str  # e.g., "gpt-4", "gpt-3.5-turbo"
    prompt: str
    context_ids: Optional[List[str]] = None
    max_tokens: Optional[int] = 4000


class ModelRunResponse(BaseModel):
    """Response with run details."""
    id: str
    status: str
    prompt: str
    estimated_tokens: int
    model: str
    created_at: str


class TokenEstimateRequest(BaseModel):
    """Request for token estimation."""
    text: str
    method: str = "precise"  # "naive" or "precise"


class TokenEstimateResponse(BaseModel):
    """Token estimate result."""
    text_length: int
    tokens: int
    method: str


# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(prefix="/v1/vibeforge", tags=["VibeForge"])


# ============================================================================
# EXAMPLE 1: Basic Token Estimation Endpoint
# ============================================================================

@router.post("/estimate-tokens", response_model=TokenEstimateResponse)
async def estimate_tokens_endpoint(request: TokenEstimateRequest):
    """
    Estimate tokens for arbitrary text.
    
    This demonstrates the two token estimation methods:
    - naive: Very fast, ~1 microsecond (4 chars = 1 token)
    - precise: More accurate, ~10 microseconds (word-count based)
    """
    if request.method == "naive":
        tokens = estimate_tokens(request.text)
    elif request.method == "precise":
        tokens = estimate_tokens_precise(request.text)
    else:
        raise HTTPException(400, "method must be 'naive' or 'precise'")
    
    return TokenEstimateResponse(
        text_length=len(request.text),
        tokens=tokens,
        method=request.method,
    )


# ============================================================================
# EXAMPLE 2: Create Run with Prompt Building
# ============================================================================

# Mock database functions (replace with real ones)
def get_contexts_from_ids(context_ids: List[str]) -> List[str]:
    """Fetch context blocks by IDs (mock implementation)."""
    contexts_db = {
        "ctx-001": "You are an expert Python engineer with 10+ years experience.",
        "ctx-002": "The codebase uses FastAPI, Pydantic, and async/await.",
        "ctx-003": "Code style: PEP 8, type hints required, max line length 100.",
    }
    return [contexts_db.get(cid, "") for cid in (context_ids or [])]


def save_run_to_storage(run_data: dict) -> None:
    """Save run record to storage (mock implementation)."""
    print(f"[STORAGE] Saved run {run_data['id']}")
    # In real implementation: json_storage.create_run() or database query


@router.post("/run", response_model=ModelRunResponse, status_code=201)
async def create_run(request: CreateRunRequest):
    """
    Create a model run with Rust-powered prompt building and token estimation.
    
    This demonstrates the complete workflow:
    1. Fetch context blocks
    2. Build complete prompt using Rust function
    3. Estimate tokens for the complete prompt
    4. Create run record with Rust function
    5. Validate token budget
    6. Return response
    """
    
    # Step 1: Get contexts
    contexts = get_contexts_from_ids(request.context_ids or [])
    
    # Step 2: Build complete prompt using Rust extension
    # The build_prompt() function combines:
    # - All context blocks
    # - User's prompt
    # Into a properly formatted prompt with markdown structure
    full_prompt = build_prompt(
        contexts=contexts,
        prompt=request.prompt,
    )
    
    # Step 3: Estimate tokens for the complete prompt
    # Uses the precise word-count based estimation
    estimated_tokens = estimate_tokens_for_prompt(
        contexts=contexts,
        prompt=request.prompt,
    )
    
    # Step 4: Check token budget
    max_tokens = request.max_tokens or 4000
    if estimated_tokens > max_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt too large: {estimated_tokens} > {max_tokens} tokens"
        )
    
    # Step 5: Create run record using Rust function
    # Returns JSON string with UUID, timestamps, status, etc.
    run_json = build_initial_run(
        model=request.model,
        prompt=request.prompt,
    )
    run_data = json.loads(run_json)
    
    # Add workspace context
    run_data["workspace_id"] = request.workspace_id
    run_data["estimated_tokens"] = estimated_tokens
    run_data["full_prompt"] = full_prompt  # Store for later use
    
    # Step 6: Persist to storage
    save_run_to_storage(run_data)
    
    # Step 7: Return response
    return ModelRunResponse(
        id=run_data["id"],
        status=run_data["status"],
        prompt=run_data["prompt"],
        estimated_tokens=estimated_tokens,
        model=request.model,
        created_at=run_data["created_at"],
    )


# ============================================================================
# EXAMPLE 3: Prompt Preview Endpoint
# ============================================================================

class PromptPreviewRequest(BaseModel):
    """Request to preview a built prompt."""
    context_ids: Optional[List[str]] = None
    prompt: str


class PromptPreviewResponse(BaseModel):
    """Preview of built prompt with metadata."""
    built_prompt: str
    prompt_length: int
    estimated_tokens: int
    context_blocks_used: int


@router.post("/preview-prompt", response_model=PromptPreviewResponse)
async def preview_prompt(request: PromptPreviewRequest):
    """
    Preview what the full prompt will look like.
    
    Useful for:
    - Testing context combinations
    - Verifying token budgets before execution
    - Debugging prompt formatting
    """
    
    contexts = get_contexts_from_ids(request.context_ids or [])
    
    # Build the prompt
    built = build_prompt(
        contexts=contexts,
        prompt=request.prompt,
    )
    
    # Estimate tokens
    tokens = estimate_tokens_for_prompt(
        contexts=contexts,
        prompt=request.prompt,
    )
    
    return PromptPreviewResponse(
        built_prompt=built,
        prompt_length=len(built),
        estimated_tokens=tokens,
        context_blocks_used=len(contexts),
    )


# ============================================================================
# EXAMPLE 4: Advanced - Using PromptContext Class
# ============================================================================

class ContextSessionRequest(BaseModel):
    """Request to manage a context session."""
    system_prompt: str
    user_prompt: str
    additional_contexts: Optional[List[str]] = None


class ContextSessionResponse(BaseModel):
    """Session with managed contexts."""
    merged_prompt: str
    token_count: int
    context_count: int


@router.post("/context-session", response_model=ContextSessionResponse)
async def manage_context_session(request: ContextSessionRequest):
    """
    Demonstrate advanced PromptContext usage for stateful context management.
    
    PromptContext is useful for:
    - Building prompts incrementally
    - Tracking token counts across multiple context additions
    - Merging contexts with consistent formatting
    """
    
    # Initialize stateful context manager
    ctx = PromptContext(
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
    )
    
    # Add contexts incrementally
    for context_text in (request.additional_contexts or []):
        ctx.add_context(context_text)
    
    # Get merged prompt
    merged = ctx.merge_contexts()
    
    # Recalculate and get final token count
    ctx.recalculate_tokens()
    
    return ContextSessionResponse(
        merged_prompt=merged,
        token_count=ctx.total_tokens_estimated,
        context_count=len(ctx.context_blocks),
    )


# ============================================================================
# EXAMPLE 5: Batch Processing with Token Tracking
# ============================================================================

class BatchRunRequest(BaseModel):
    """Request to process multiple prompts."""
    model: str
    prompts: List[str]
    context_ids: Optional[List[str]] = None


class BatchRunResponse(BaseModel):
    """Response with batch processing results."""
    run_ids: List[str]
    total_tokens: int
    average_tokens: int


@router.post("/batch-runs", response_model=BatchRunResponse)
async def batch_process_runs(request: BatchRunRequest):
    """
    Process multiple prompts in a batch.
    
    This demonstrates:
    - Reusing contexts for efficiency
    - Token aggregation
    - Batch run creation
    """
    
    contexts = get_contexts_from_ids(request.context_ids or [])
    run_ids = []
    total_tokens = 0
    
    for prompt in request.prompts:
        # Build and estimate for each prompt
        tokens = estimate_tokens_for_prompt(
            contexts=contexts,
            prompt=prompt,
        )
        
        # Create run
        run_json = build_initial_run(request.model, prompt)
        run_data = json.loads(run_json)
        
        run_ids.append(run_data["id"])
        total_tokens += tokens
        
        # Save to storage
        save_run_to_storage(run_data)
    
    return BatchRunResponse(
        run_ids=run_ids,
        total_tokens=total_tokens,
        average_tokens=total_tokens // len(request.prompts) if request.prompts else 0,
    )


# ============================================================================
# EXAMPLE 6: Token Budget Tracking
# ============================================================================

class TokenBudgetCheckRequest(BaseModel):
    """Check if prompts fit within token budget."""
    budget: int  # Max tokens allowed
    prompts: List[str]
    context_ids: Optional[List[str]] = None


class TokenBudgetCheckResponse(BaseModel):
    """Budget check results."""
    budget: int
    total_tokens: int
    fits_budget: bool
    available: int
    over_by: int


@router.post("/check-budget", response_model=TokenBudgetCheckResponse)
async def check_token_budget(request: TokenBudgetCheckCheckRequest):
    """
    Check if multiple prompts fit within a token budget.
    
    Useful for cost control and planning.
    """
    
    contexts = get_contexts_from_ids(request.context_ids or [])
    total_tokens = 0
    
    for prompt in request.prompts:
        tokens = estimate_tokens_for_prompt(contexts, prompt)
        total_tokens += tokens
    
    fits = total_tokens <= request.budget
    available = request.budget - total_tokens if fits else 0
    over_by = total_tokens - request.budget if not fits else 0
    
    return TokenBudgetCheckResponse(
        budget=request.budget,
        total_tokens=total_tokens,
        fits_budget=fits,
        available=available,
        over_by=over_by,
    )


# ============================================================================
# USAGE IN MAIN APP
# ============================================================================

"""
To use this in your main FastAPI app:

from fastapi import FastAPI
from integration_example import router

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

Then test endpoints:

    # Estimate tokens
    curl -X POST http://localhost:8000/v1/vibeforge/estimate-tokens \\
        -H "Content-Type: application/json" \\
        -d '{"text": "Hello world", "method": "precise"}'
    
    # Create run with prompt building
    curl -X POST http://localhost:8000/v1/vibeforge/run \\
        -H "Content-Type: application/json" \\
        -d '{
            "workspace_id": "test",
            "model": "gpt-4",
            "prompt": "What is AI?",
            "context_ids": ["ctx-001", "ctx-002"]
        }'
    
    # Preview built prompt
    curl -X POST http://localhost:8000/v1/vibeforge/preview-prompt \\
        -H "Content-Type: application/json" \\
        -d '{
            "context_ids": ["ctx-001"],
            "prompt": "Implement a function"
        }'
"""
