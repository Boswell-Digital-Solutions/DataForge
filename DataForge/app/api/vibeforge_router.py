"""
VibeForge Learning Layer API Router

Provides endpoints for tracking wizard interactions, project outcomes,
model performance, and user preferences to enable adaptive learning.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import User
from app.models.vibeforge_models import ProjectType, OutcomeStatus
from app.models.vibeforge_schemas import (
    VibeForgeProjectCreate,
    VibeForgeProjectUpdate,
    VibeForgeProjectResponse,
    ProjectSessionCreate,
    ProjectSessionUpdate,
    ProjectSessionResponse,
    StackOutcomeCreate,
    StackOutcomeUpdate,
    StackOutcomeResponse,
    ModelPerformanceCreate,
    ModelPerformanceUpdate,
    ModelPerformanceResponse,
    LanguagePreferenceResponse,
    LanguagePreferenceUpdate,
    StackSuccessRate,
    LanguageTrend,
    UserPreferenceSummary
)
from app.services.vibeforge_service import (
    ProjectService,
    SessionService,
    OutcomeService,
    PerformanceService,
    PreferenceService
)
from app.utils.auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/vibeforge", tags=["vibeforge-learning"])


# ============================================================================
# Project Endpoints
# ============================================================================

@router.post("/projects", response_model=VibeForgeProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: VibeForgeProjectCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Create a new VibeForge project record.
    
    This endpoint logs a project created through the wizard,
    capturing all selections and metadata for learning purposes.
    """
    # Override user_id with authenticated user if available
    if current_user:
        project.user_id = current_user.id
    
    return ProjectService.create(db, project)


@router.get("/projects/{project_id}", response_model=VibeForgeProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific VibeForge project by ID."""
    project = ProjectService.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects", response_model=List[VibeForgeProjectResponse])
def list_projects(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    project_type: Optional[ProjectType] = Query(None, description="Filter by project type"),
    stack_id: Optional[str] = Query(None, description="Filter by stack ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List VibeForge projects with optional filters.
    
    If user_id is not provided and user is authenticated, returns their projects.
    """
    if user_id:
        return ProjectService.get_by_user(db, user_id, skip, limit)
    elif current_user:
        return ProjectService.get_by_user(db, current_user.id, skip, limit)
    elif project_type:
        return ProjectService.get_by_type(db, project_type, skip, limit)
    elif stack_id:
        return ProjectService.get_by_stack(db, stack_id, skip, limit)
    else:
        return ProjectService.get_recent(db, days=30, limit=limit)


@router.patch("/projects/{project_id}", response_model=VibeForgeProjectResponse)
def update_project(
    project_id: int,
    project_update: VibeForgeProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update a VibeForge project."""
    project = ProjectService.update(db, project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Delete a VibeForge project and all related data."""
    success = ProjectService.delete(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")


# ============================================================================
# Session Endpoints
# ============================================================================

@router.post("/sessions", response_model=ProjectSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session: ProjectSessionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new wizard session record.
    
    This endpoint starts tracking a user's journey through the wizard,
    capturing all interactions for behavior analysis.
    """
    return SessionService.create(db, session)


@router.get("/sessions/{session_id}", response_model=ProjectSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific wizard session by ID."""
    session = SessionService.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/projects/{project_id}/sessions", response_model=List[ProjectSessionResponse])
def list_project_sessions(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get all wizard sessions for a specific project."""
    return SessionService.get_by_project(db, project_id)


@router.patch("/sessions/{session_id}", response_model=ProjectSessionResponse)
def update_session(
    session_id: int,
    session_update: ProjectSessionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a wizard session.
    
    Use this to track incremental changes as the user progresses through steps,
    or to mark the session as completed/abandoned.
    """
    session = SessionService.update(db, session_id, session_update)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/complete", response_model=ProjectSessionResponse)
def complete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark a session as completed.
    
    Automatically calculates session duration.
    """
    session = SessionService.mark_completed(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/abandon", response_model=ProjectSessionResponse)
def abandon_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Mark a session as abandoned."""
    session = SessionService.mark_abandoned(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ============================================================================
# Outcome Endpoints
# ============================================================================

@router.post("/outcomes", response_model=StackOutcomeResponse, status_code=status.HTTP_201_CREATED)
def create_outcome(
    outcome: StackOutcomeCreate,
    db: Session = Depends(get_db)
):
    """
    Record a stack outcome.
    
    This endpoint logs the success/failure of a project build, test, or deployment,
    enabling the system to learn which stacks work well for which scenarios.
    """
    return OutcomeService.create(db, outcome)


@router.get("/outcomes/{outcome_id}", response_model=StackOutcomeResponse)
def get_outcome(
    outcome_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific outcome record by ID."""
    outcome = OutcomeService.get(db, outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome


@router.get("/projects/{project_id}/outcomes", response_model=List[StackOutcomeResponse])
def list_project_outcomes(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get all outcome records for a specific project."""
    return OutcomeService.get_by_project(db, project_id)


@router.get("/stacks/{stack_id}/outcomes", response_model=List[StackOutcomeResponse])
def list_stack_outcomes(
    stack_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all outcome records for a specific stack."""
    return OutcomeService.get_by_stack(db, stack_id, skip, limit)


@router.patch("/outcomes/{outcome_id}", response_model=StackOutcomeResponse)
def update_outcome(
    outcome_id: int,
    outcome_update: StackOutcomeUpdate,
    db: Session = Depends(get_db)
):
    """Update an outcome record."""
    outcome = OutcomeService.update(db, outcome_id, outcome_update)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome


# ============================================================================
# Model Performance Endpoints
# ============================================================================

@router.post("/performance", response_model=ModelPerformanceResponse, status_code=status.HTTP_201_CREATED)
def create_performance_record(
    performance: ModelPerformanceCreate,
    db: Session = Depends(get_db)
):
    """
    Record LLM model performance.
    
    This endpoint logs model usage, response times, token consumption,
    and recommendation acceptance for A/B testing and effectiveness tracking.
    """
    return PerformanceService.create(db, performance)


@router.get("/performance/{performance_id}", response_model=ModelPerformanceResponse)
def get_performance_record(
    performance_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific performance record by ID."""
    perf = PerformanceService.get(db, performance_id)
    if not perf:
        raise HTTPException(status_code=404, detail="Performance record not found")
    return perf


@router.get("/sessions/{session_id}/performance", response_model=List[ModelPerformanceResponse])
def list_session_performance(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get all performance records for a specific session."""
    return PerformanceService.get_by_session(db, session_id)


@router.patch("/performance/{performance_id}", response_model=ModelPerformanceResponse)
def update_performance_record(
    performance_id: int,
    performance_update: ModelPerformanceUpdate,
    db: Session = Depends(get_db)
):
    """Update a performance record (typically to add user feedback)."""
    perf = PerformanceService.update(db, performance_id, performance_update)
    if not perf:
        raise HTTPException(status_code=404, detail="Performance record not found")
    return perf


# ============================================================================
# Language Preference Endpoints
# ============================================================================

@router.get("/preferences/{user_id}", response_model=List[LanguagePreferenceResponse])
def get_user_preferences(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get language preferences for a user.
    
    Returns all language usage history, including selection counts,
    pairing data, and success metrics.
    """
    return PreferenceService.get_by_user(db, user_id)


@router.get("/preferences/{user_id}/favorites", response_model=List[LanguagePreferenceResponse])
def get_favorite_languages(
    user_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get user's favorite languages by selection frequency."""
    return PreferenceService.get_favorites(db, user_id, limit)


@router.get("/preferences/{user_id}/summary", response_model=UserPreferenceSummary)
def get_user_summary(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive preference summary for a user.
    
    Includes favorite languages/stacks, project type preferences,
    and overall success metrics.
    """
    return PreferenceService.get_user_summary(db, user_id)


@router.post("/preferences/track-view")
def track_language_view(
    user_id: int,
    language_id: str,
    language_name: str,
    db: Session = Depends(get_db)
):
    """Track that a user viewed a language option."""
    PreferenceService.increment_viewed(db, user_id, language_id, language_name)
    return {"status": "tracked"}


@router.post("/preferences/track-consider")
def track_language_consider(
    user_id: int,
    language_id: str,
    language_name: str,
    db: Session = Depends(get_db)
):
    """Track that a user considered a language (clicked for details)."""
    PreferenceService.increment_considered(db, user_id, language_id, language_name)
    return {"status": "tracked"}


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/stack-success", response_model=StackSuccessRate)
def get_stack_success_rate(
    stack_id: str,
    project_type: Optional[ProjectType] = Query(None, description="Filter by project type"),
    db: Session = Depends(get_db)
):
    """
    Get success rate analytics for a stack.
    
    Returns total uses, success/failure counts, average satisfaction,
    and performance metrics.
    """
    success_rate = OutcomeService.get_stack_success_rate(db, stack_id, project_type)
    if not success_rate:
        raise HTTPException(
            status_code=404,
            detail=f"No outcome data found for stack '{stack_id}'"
        )
    return success_rate


@router.get("/analytics/model-acceptance")
def get_model_acceptance_rate(
    provider: str,
    model_name: str,
    db: Session = Depends(get_db)
):
    """
    Get recommendation acceptance rate for a specific model.
    
    Useful for A/B testing and model effectiveness comparison.
    """
    acceptance_rate = PerformanceService.get_acceptance_rate(db, provider, model_name)
    return {
        "provider": provider,
        "model_name": model_name,
        "acceptance_rate": acceptance_rate,
        "percentage": f"{acceptance_rate * 100:.1f}%"
    }


@router.get("/analytics/abandoned-sessions")
def get_abandoned_sessions(
    days: int = Query(7, ge=1, le=365, description="Look back window in days"),
    db: Session = Depends(get_db)
):
    """
    Get sessions that appear abandoned (not completed within time window).
    
    Useful for understanding drop-off points in the wizard.
    """
    abandoned = SessionService.get_abandoned_sessions(db, days)
    return {
        "count": len(abandoned),
        "sessions": [{"id": s.id, "project_id": s.project_id, "started_at": s.session_started_at} for s in abandoned]
    }


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
def health_check():
    """Health check endpoint for VibeForge learning layer."""
    return {
        "status": "healthy",
        "service": "vibeforge-learning",
        "version": "1.0.0"
    }
