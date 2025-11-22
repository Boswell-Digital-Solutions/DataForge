"""
DataForge - Runs Service Layer

Service layer for managing prompt execution runs with repository pattern.
Handles CRUD operations, cost calculations, and analytics queries.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.models.runs_models import Run, ModelResult
from app.models.runs_schemas import (
    RunCreate, RunSummary, RunDetailResponse, 
    ListRunsResponse, UsageMetrics, DeleteRunResponse,
    ModelResultCreate
)

logger = logging.getLogger(__name__)


# ============================================================================
# Cost Calculation
# ============================================================================

# Pricing per 1M tokens (updated as of Nov 2025)
PRICING: Dict[str, Dict[str, Dict[str, float]]] = {
    "anthropic": {
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,   # $3 per 1M input tokens
            "output": 15.00  # $15 per 1M output tokens
        },
        "claude-3-5-sonnet-latest": {
            "input": 3.00,
            "output": 15.00
        },
        "claude-3-opus-20240229": {
            "input": 15.00,
            "output": 75.00
        },
        "claude-3-sonnet-20240229": {
            "input": 3.00,
            "output": 15.00
        },
        "claude-3-haiku-20240307": {
            "input": 0.25,
            "output": 1.25
        }
    },
    "openai": {
        "gpt-4o": {
            "input": 2.50,
            "output": 10.00
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60
        },
        "gpt-4-turbo": {
            "input": 10.00,
            "output": 30.00
        },
        "gpt-4": {
            "input": 30.00,
            "output": 60.00
        },
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50
        }
    },
    "ollama": {
        # Local models have no cost
        "*": {
            "input": 0.0,
            "output": 0.0
        }
    }
}


def calculate_cost(
    provider: str,
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int
) -> float:
    """
    Calculate cost in USD for a model execution.
    
    Args:
        provider: Provider name (e.g., "anthropic", "openai", "ollama")
        model_id: Model identifier
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
    
    Returns:
        Cost in USD
    """
    provider = provider.lower()
    
    # Ollama models are free
    if provider == "ollama":
        return 0.0
    
    # Get pricing for provider
    if provider not in PRICING:
        logger.warning(f"Unknown provider '{provider}', defaulting to $0 cost")
        return 0.0
    
    provider_pricing = PRICING[provider]
    
    # Find model pricing (exact match or wildcard)
    model_pricing = provider_pricing.get(model_id)
    if not model_pricing:
        # Try wildcard
        model_pricing = provider_pricing.get("*")
        if not model_pricing:
            logger.warning(
                f"Unknown model '{model_id}' for provider '{provider}', "
                "defaulting to $0 cost"
            )
            return 0.0
    
    # Calculate cost per million tokens
    input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
    
    return round(input_cost + output_cost, 6)  # Round to 6 decimal places


# ============================================================================
# Repository Pattern
# ============================================================================

class RunsRepository:
    """Repository for Run and ModelResult database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_run(self, run_data: RunCreate) -> Run:
        """
        Create a new run with its model results.
        
        Args:
            run_data: Run creation data
        
        Returns:
            Created Run instance
        """
        # Calculate costs for each result
        total_tokens = 0
        total_cost = 0.0
        
        model_results = []
        for result_data in run_data.results:
            cost = calculate_cost(
                result_data.provider,
                result_data.model_id,
                result_data.prompt_tokens,
                result_data.completion_tokens
            )
            
            total_tokens += result_data.total_tokens
            total_cost += cost
            
            model_result = ModelResult(
                run_id=run_data.run_id,
                model_id=result_data.model_id,
                provider=result_data.provider,
                output=result_data.output,
                prompt_tokens=result_data.prompt_tokens,
                completion_tokens=result_data.completion_tokens,
                total_tokens=result_data.total_tokens,
                cost_usd=cost,
                latency_ms=result_data.latency_ms,
                status=result_data.status,
                error_message=result_data.error_message
            )
            model_results.append(model_result)
        
        # Determine overall status
        if all(r.status == "success" for r in run_data.results):
            status = "success"
        elif any(r.status == "success" for r in run_data.results):
            status = "partial"
        else:
            status = "error"
        
        # Create run
        run = Run(
            run_id=run_data.run_id,
            workspace_id=run_data.workspace_id,
            prompt_snapshot=run_data.prompt_snapshot,
            context_block_ids=run_data.context_block_ids,
            total_latency_ms=run_data.total_latency_ms,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            tags=run_data.tags,
            notes=run_data.notes,
            status=status
        )
        
        # Add to session
        self.db.add(run)
        for result in model_results:
            self.db.add(result)
        
        self.db.commit()
        self.db.refresh(run)
        
        logger.info(
            f"Created run {run.run_id}: {total_tokens} tokens, "
            f"${total_cost:.4f}, status={status}"
        )
        
        return run
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID with its results."""
        return self.db.query(Run).filter(Run.run_id == run_id).first()
    
    def list_runs(
        self,
        workspace_id: Optional[str] = None,
        model_id: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Run], int]:
        """
        List runs with filters and pagination.
        
        Returns:
            Tuple of (runs, total_count)
        """
        query = self.db.query(Run)
        
        # Apply filters
        if workspace_id:
            query = query.filter(Run.workspace_id == workspace_id)
        
        if status:
            query = query.filter(Run.status == status)
        
        if start_date:
            query = query.filter(Run.created_at >= start_date)
        
        if end_date:
            query = query.filter(Run.created_at <= end_date)
        
        if tags:
            # Filter by any tag match (OR condition)
            for tag in tags:
                query = query.filter(Run.tags.contains([tag]))
        
        if model_id:
            # Join with model_results to filter by model
            query = query.join(ModelResult).filter(
                ModelResult.model_id == model_id
            ).distinct()
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        runs = query.order_by(desc(Run.created_at)).offset(offset).limit(page_size).all()
        
        return runs, total
    
    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run and its results.
        
        Returns:
            True if deleted, False if not found
        """
        run = self.get_run(run_id)
        if not run:
            return False
        
        self.db.delete(run)
        self.db.commit()
        
        logger.info(f"Deleted run {run_id}")
        return True
    
    def get_usage_metrics(
        self,
        workspace_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate usage metrics for a workspace.
        
        Returns:
            Dictionary with aggregated metrics
        """
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Query runs in date range
        runs_query = self.db.query(Run).filter(
            and_(
                Run.workspace_id == workspace_id,
                Run.created_at >= start_date,
                Run.created_at <= end_date
            )
        )
        
        # Total metrics
        total_runs = runs_query.count()
        total_tokens = runs_query.with_entities(
            func.sum(Run.total_tokens)
        ).scalar() or 0
        total_cost = runs_query.with_entities(
            func.sum(Run.total_cost_usd)
        ).scalar() or 0.0
        
        # Per-model metrics
        model_stats = self.db.query(
            ModelResult.model_id,
            func.count(ModelResult.id).label('run_count'),
            func.sum(ModelResult.total_tokens).label('total_tokens'),
            func.sum(ModelResult.cost_usd).label('total_cost')
        ).join(Run).filter(
            and_(
                Run.workspace_id == workspace_id,
                Run.created_at >= start_date,
                Run.created_at <= end_date
            )
        ).group_by(ModelResult.model_id).all()
        
        runs_by_model = {}
        tokens_by_model = {}
        cost_by_model = {}
        
        for stat in model_stats:
            runs_by_model[stat.model_id] = stat.run_count
            tokens_by_model[stat.model_id] = stat.total_tokens or 0
            cost_by_model[stat.model_id] = round(stat.total_cost or 0.0, 4)
        
        return {
            "workspace_id": workspace_id,
            "total_runs": total_runs,
            "total_tokens": int(total_tokens),
            "total_cost_usd": round(float(total_cost), 4),
            "runs_by_model": runs_by_model,
            "tokens_by_model": tokens_by_model,
            "cost_by_model": cost_by_model,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }


# ============================================================================
# Service Layer (Business Logic)
# ============================================================================

class RunsService:
    """Service for managing runs with business logic."""
    
    def __init__(self, db: Session):
        self.repo = RunsRepository(db)
    
    def log_run(self, run_data: RunCreate) -> Dict[str, Any]:
        """Log a new run."""
        try:
            run = self.repo.create_run(run_data)
            return {
                "status": "success",
                "run_id": run.run_id,
                "message": "Run logged successfully"
            }
        except Exception as e:
            logger.error(f"Failed to log run {run_data.run_id}: {e}", exc_info=True)
            raise
    
    def get_run_details(self, run_id: str) -> Optional[RunDetailResponse]:
        """Get detailed run information."""
        run = self.repo.get_run(run_id)
        if not run:
            return None
        
        return RunDetailResponse.model_validate(run)
    
    def list_runs(
        self,
        workspace_id: Optional[str] = None,
        model_id: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> ListRunsResponse:
        """List runs with filters."""
        runs, total = self.repo.list_runs(
            workspace_id=workspace_id,
            model_id=model_id,
            status=status,
            tags=tags,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        # Convert to summaries
        summaries = []
        for run in runs:
            model_ids = [r.model_id for r in run.results]
            # Truncate prompt to 200 chars for summary
            prompt_preview = run.prompt_snapshot[:200]
            if len(run.prompt_snapshot) > 200:
                prompt_preview += "..."
            
            summaries.append(RunSummary(
                run_id=run.run_id,
                workspace_id=run.workspace_id,
                prompt_snapshot=prompt_preview,
                model_ids=model_ids,
                total_tokens=run.total_tokens,
                total_cost_usd=run.total_cost_usd,
                status=run.status,
                created_at=run.created_at
            ))
        
        has_more = (page * page_size) < total
        
        return ListRunsResponse(
            runs=summaries,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
    
    def delete_run(self, run_id: str) -> DeleteRunResponse:
        """Delete a run."""
        deleted = self.repo.delete_run(run_id)
        
        if deleted:
            return DeleteRunResponse(
                status="success",
                message=f"Run {run_id} deleted",
                run_id=run_id
            )
        else:
            return DeleteRunResponse(
                status="error",
                message=f"Run {run_id} not found",
                run_id=run_id
            )
    
    def get_usage_metrics(
        self,
        workspace_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageMetrics:
        """Get usage metrics for a workspace."""
        metrics_data = self.repo.get_usage_metrics(
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return UsageMetrics(**metrics_data)
