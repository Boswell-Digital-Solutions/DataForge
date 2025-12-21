"""
Multi-AI Planning System - Learning Router

API endpoints for recording planning outcomes and retrieving learned recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.planning_models import (
    PlanningOutcome,
    PlanningModelPerformance,
    AIEstimationFeedback
)
from app.models.planning_schemas import (
    PlanningOutcomeCreate,
    PlanningOutcomeResponse,
    ExecutionResultUpdate,
    UserFeedbackUpdate,
    AIEstimationFeedbackCreate,
    AIEstimationFeedbackResponse,
    ModelPerformanceResponse,
    StageModelRecommendations,
    TimeEstimateRecommendation,
    IterationRecommendation,
    ModelRecommendation
)

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


# ============================================================================
# Recording Endpoints (Write Operations)
# ============================================================================

@router.post("/planning-outcomes", response_model=dict)
async def record_planning_outcome(
    outcome: PlanningOutcomeCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Record outcome of a multi-AI planning session.

    Triggers background job to update model performance aggregates.
    """
    # Create outcome record
    record = PlanningOutcome(
        session_id=outcome.session_id,
        workflow_type=outcome.workflow_type,
        task_type=outcome.task_type,
        request_complexity=outcome.request_complexity,
        codebase_context=outcome.codebase_context,
        stages=[s.model_dump() for s in outcome.stages],
        total_duration_ms=outcome.total_duration_ms,
        total_tokens_used=outcome.total_tokens_used,
        total_cost_cents=outcome.total_cost_cents,
        iteration_count=outcome.iteration_count
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    # Trigger async model performance update
    background_tasks.add_task(
        update_model_performance_from_outcome,
        str(record.id),
        outcome.model_dump(),
        db
    )

    return {
        "id": str(record.id),
        "status": "recorded"
    }


@router.patch("/planning-outcomes/{outcome_id}/execution", response_model=dict)
async def update_execution_result(
    outcome_id: str,
    result: ExecutionResultUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Update planning outcome with execution results.

    Called after Claude Code executes the generated plan.
    """
    outcome = db.query(PlanningOutcome).filter(PlanningOutcome.id == outcome_id).first()

    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    # Update execution fields
    outcome.execution_started = True
    outcome.execution_success = result.success
    outcome.execution_duration_seconds = result.duration_seconds
    outcome.tasks_completed = result.tasks_completed
    outcome.tasks_failed = result.tasks_failed

    db.commit()

    # Re-calculate model performance with execution feedback
    background_tasks.add_task(
        recalculate_model_quality_with_execution,
        str(outcome_id),
        db
    )

    return {"status": "updated"}


@router.patch("/planning-outcomes/{outcome_id}/feedback", response_model=dict)
async def record_user_feedback(
    outcome_id: str,
    feedback: UserFeedbackUpdate,
    db: Session = Depends(get_db)
):
    """Record user feedback on planning session."""
    outcome = db.query(PlanningOutcome).filter(PlanningOutcome.id == outcome_id).first()

    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    outcome.user_rating = feedback.rating
    outcome.user_feedback = feedback.feedback
    outcome.plan_was_modified = feedback.plan_was_modified
    outcome.modification_extent = feedback.modification_extent

    db.commit()

    return {"status": "updated"}


@router.post("/estimation-feedback", response_model=dict)
async def record_estimation_feedback(
    feedback_list: List[AIEstimationFeedbackCreate],
    db: Session = Depends(get_db)
):
    """Record AI execution time feedback for learning."""
    for item in feedback_list:
        # Calculate accuracy ratio
        accuracy_ratio = item.actual_minutes / item.estimated_minutes if item.estimated_minutes > 0 else None

        record = AIEstimationFeedback(
            task_category=item.task_category,
            task_complexity=item.task_complexity,
            estimated_minutes=item.estimated_minutes,
            actual_minutes=item.actual_minutes,
            accuracy_ratio=accuracy_ratio,
            executor_type=item.executor_type,
            model_used=item.model_used,
            codebase_lines=item.codebase_lines,
            factors=item.factors,
            session_id=item.session_id
        )
        db.add(record)

    db.commit()

    return {"recorded": len(feedback_list)}


# ============================================================================
# Recommendation Endpoints (Read Operations)
# ============================================================================

@router.get("/model-performance", response_model=List[ModelPerformanceResponse])
async def get_model_performance(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    stage_type: Optional[str] = None,
    task_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get model performance metrics.

    Filter by model, provider, stage_type, and/or task_type.
    """
    query = db.query(PlanningModelPerformance)

    if model:
        query = query.filter(PlanningModelPerformance.model == model)
    if provider:
        query = query.filter(PlanningModelPerformance.provider == provider)
    if stage_type:
        query = query.filter(PlanningModelPerformance.stage_type == stage_type)
    if task_type:
        query = query.filter(PlanningModelPerformance.task_type == task_type)

    results = query.all()
    return results


@router.get("/recommendations/stage-models", response_model=StageModelRecommendations)
async def get_stage_model_recommendations(
    task_type: str = "general",
    db: Session = Depends(get_db)
):
    """
    Get recommended models for each planning stage based on historical performance.

    Returns optimal model selection for all 4 stages: initial, review, refinement, final.
    """
    stages = ["initial", "review", "refinement", "final"]
    recommendations = {}
    total_samples = 0

    for stage in stages:
        # Get top performing model for this stage
        top_model = db.query(PlanningModelPerformance).filter(
            PlanningModelPerformance.stage_type == stage,
            PlanningModelPerformance.task_type == task_type,
            PlanningModelPerformance.sample_count > 0
        ).order_by(
            PlanningModelPerformance.ema_quality.desc(),
            PlanningModelPerformance.success_rate.desc()
        ).first()

        if top_model:
            total_samples += top_model.sample_count
            recommendations[stage] = ModelRecommendation(
                model=top_model.model,
                provider=top_model.provider,
                reason=f"Best quality (EMA: {top_model.ema_quality:.2f}) with {top_model.success_rate:.1%} success rate",
                confidence=min(top_model.sample_count / 10, 1.0)  # Full confidence at 10+ samples
            )
        else:
            # Default recommendations if no data
            defaults = {
                "initial": ("gpt-4", "openai"),
                "review": ("claude-3-opus", "anthropic"),
                "refinement": ("gpt-4", "openai"),
                "final": ("claude-3-opus", "anthropic")
            }
            model, provider = defaults[stage]
            recommendations[stage] = ModelRecommendation(
                model=model,
                provider=provider,
                reason="Default recommendation (no historical data)",
                confidence=0.3
            )

    overall_confidence = min(total_samples / 40, 1.0)  # Full confidence at 10 samples per stage

    return StageModelRecommendations(
        initial=recommendations["initial"],
        review=recommendations["review"],
        refinement=recommendations["refinement"],
        final=recommendations["final"],
        confidence=overall_confidence,
        based_on_samples=total_samples
    )


@router.get("/recommendations/time-estimate", response_model=TimeEstimateRecommendation)
async def get_time_estimate(
    task_category: str,
    task_complexity: str = "medium",
    executor_type: str = "claude_code",
    db: Session = Depends(get_db)
):
    """
    Get AI execution time estimate based on historical data.

    Returns recommended time estimate with confidence interval.
    """
    # Get recent feedback for similar tasks
    feedback = db.query(AIEstimationFeedback).filter(
        AIEstimationFeedback.task_category == task_category,
        AIEstimationFeedback.task_complexity == task_complexity,
        AIEstimationFeedback.executor_type == executor_type
    ).order_by(
        AIEstimationFeedback.created_at.desc()
    ).limit(50).all()

    if not feedback:
        # Return default estimate
        defaults = {
            "simple": 30,
            "medium": 60,
            "complex": 120
        }
        return TimeEstimateRecommendation(
            estimated_minutes=defaults.get(task_complexity, 60),
            confidence=0.2,
            based_on_samples=0,
            note="Default estimate (no historical data)"
        )

    # Calculate weighted average (recent feedback weighted higher)
    actual_times = [f.actual_minutes for f in feedback]
    weights = [1 / (i + 1) for i in range(len(actual_times))]  # Exponential decay
    weighted_avg = sum(t * w for t, w in zip(actual_times, weights)) / sum(weights)

    # Calculate confidence interval (std dev)
    import statistics
    std_dev = statistics.stdev(actual_times) if len(actual_times) > 1 else 0
    confidence_interval = (max(0, weighted_avg - std_dev), weighted_avg + std_dev)

    return TimeEstimateRecommendation(
        estimated_minutes=weighted_avg,
        confidence=min(len(feedback) / 20, 1.0),
        confidence_interval=confidence_interval,
        based_on_samples=len(feedback),
        note=f"Based on {len(feedback)} similar tasks"
    )


@router.get("/recommendations/iteration-count", response_model=IterationRecommendation)
async def get_iteration_recommendation(
    task_type: str = "general",
    complexity: str = "medium",
    db: Session = Depends(get_db)
):
    """
    Get recommended iteration count for planning workflow.

    Returns optimal number of review iterations based on historical success rates.
    """
    # Get outcomes with different iteration counts
    outcomes = db.query(PlanningOutcome).filter(
        PlanningOutcome.task_type == task_type,
        PlanningOutcome.request_complexity == complexity,
        PlanningOutcome.execution_success.isnot(None)
    ).all()

    if not outcomes:
        # Default recommendations
        defaults = {
            "simple": (1, 1, 2),
            "medium": (2, 1, 3),
            "complex": (3, 2, 4)
        }
        recommended, min_viable, diminishing = defaults.get(complexity, (2, 1, 3))

        return IterationRecommendation(
            recommended=recommended,
            min_viable=min_viable,
            diminishing_returns=diminishing,
            confidence=0.3,
            based_on_samples=0,
            note="Default recommendation (no historical data)"
        )

    # Group by iteration count and calculate success rates
    from collections import defaultdict
    by_iterations = defaultdict(list)
    for outcome in outcomes:
        by_iterations[outcome.iteration_count].append(outcome.execution_success)

    # Find optimal iteration count
    success_rates = {
        count: sum(successes) / len(successes)
        for count, successes in by_iterations.items()
        if len(successes) >= 3  # Minimum 3 samples
    }

    if success_rates:
        recommended = max(success_rates.keys(), key=lambda k: success_rates[k])
        min_viable = min(count for count, rate in success_rates.items() if rate >= 0.7)
        diminishing = max(success_rates.keys()) + 1

        return IterationRecommendation(
            recommended=recommended,
            min_viable=min_viable,
            diminishing_returns=diminishing,
            confidence=min(len(outcomes) / 30, 1.0),
            based_on_samples=len(outcomes),
            note=f"Optimal: {recommended} iterations ({success_rates[recommended]:.1%} success rate)"
        )

    # Fallback to defaults
    defaults = {"simple": (1, 1, 2), "medium": (2, 1, 3), "complex": (3, 2, 4)}
    recommended, min_viable, diminishing = defaults.get(complexity, (2, 1, 3))

    return IterationRecommendation(
        recommended=recommended,
        min_viable=min_viable,
        diminishing_returns=diminishing,
        confidence=0.4,
        based_on_samples=len(outcomes),
        note="Insufficient data for conclusive recommendation"
    )


# ============================================================================
# Background Job Functions (Stubs for now)
# ============================================================================

def update_model_performance_from_outcome(outcome_id: str, outcome_data: dict, db: Session):
    """
    Background job to update model performance aggregates.

    TODO: Implement EMA calculations and aggregate updates.
    """
    # Placeholder - will be implemented when background jobs are set up
    pass


def recalculate_model_quality_with_execution(outcome_id: str, db: Session):
    """
    Background job to recalculate quality scores based on execution results.

    TODO: Adjust quality scores based on whether the plan actually worked.
    """
    # Placeholder - will be implemented when background jobs are set up
    pass
