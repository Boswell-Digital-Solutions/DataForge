"""
Smithy Planning Session API Router

REST API endpoints for Planning sprint persistence.
Base path: /api/v1/smithy/planning
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.smithy_planning_schemas import (
    PlanningSession,
    PlanningSessionSummary,
    PlanningSessionCreate,
    PlanningSessionUpdate,
    PlanningDeliverable,
    PlanningDeliverableCreate,
    OperationalMemorySummary,
    SessionStatus,
)
from app.api import smithy_planning_crud as crud

router = APIRouter(prefix="/api/v1/smithy/planning", tags=["smithy-planning"])


# ═══════════════════════════════════════════════════════════════════════════════
# Sessions
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/sessions", response_model=list[PlanningSessionSummary])
def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List planning sessions with optional filtering.

    Returns lightweight summaries for efficient listing.
    """
    sessions = crud.get_sessions(db, user_id=user_id, status=status, limit=limit, offset=offset)

    return [
        PlanningSessionSummary(
            id=s.id,
            user_id=s.user_id,
            status=s.status,
            request_title=s.request_title,
            created_at=s.created_at,
            completed_at=s.completed_at,
            has_deliverable=s.deliverable is not None
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=PlanningSession, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: PlanningSessionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new planning session.

    Called when a user starts a planning sprint in forge-smithy.
    """
    session = crud.create_session(db, session_data)
    return session


@router.get("/sessions/{session_id}", response_model=PlanningSession)
def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a planning session by ID.

    Includes the full deliverable and steps if available.
    """
    session = crud.get_session_by_id(db, session_id, include_deliverable=True)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )
    return session


@router.get("/sessions/by-forgeagents/{forgeagents_session_id}", response_model=PlanningSession)
def get_session_by_forgeagents_id(
    forgeagents_session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a planning session by ForgeAgents session ID.

    Useful for correlating ForgeAgents backend sessions with persisted records.
    """
    session = crud.get_session_by_forgeagents_id(db, forgeagents_session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session with ForgeAgents ID '{forgeagents_session_id}' not found"
        )
    return session


@router.patch("/sessions/{session_id}", response_model=PlanningSession)
def update_session(
    session_id: str,
    update_data: PlanningSessionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a planning session.

    Used to update status, stage outputs, and error information.
    """
    session = crud.update_session(db, session_id, update_data)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )
    return session


@router.post("/sessions/{session_id}/start", response_model=PlanningSession)
def start_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a planning session as running.

    Called when the PAORT cycle begins.
    """
    session = crud.start_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )
    return session


@router.post("/sessions/{session_id}/complete", response_model=PlanningSession)
def complete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a planning session as completed.

    Called when the PAORT cycle finishes successfully.
    """
    session = crud.complete_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )
    return session


@router.post("/sessions/{session_id}/fail", response_model=PlanningSession)
def fail_session(
    session_id: str,
    error_message: str = Query(..., description="Error message"),
    error_stage: Optional[str] = Query(None, description="Stage where error occurred"),
    db: Session = Depends(get_db)
):
    """
    Mark a planning session as failed.

    Called when the PAORT cycle encounters an error.
    """
    session = crud.fail_session(db, session_id, error_message, error_stage)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )
    return session


@router.post("/sessions/{session_id}/cancel", response_model=PlanningSession)
def cancel_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a planning session as cancelled.

    Called when the user cancels a running session.
    """
    session = crud.cancel_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a planning session.

    Also deletes the associated deliverable and steps.
    """
    deleted = crud.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Deliverables
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/sessions/{session_id}/deliverable", response_model=PlanningDeliverable)
def get_deliverable(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the deliverable for a planning session.

    Returns 404 if the session doesn't exist or has no deliverable.
    """
    # Verify session exists
    session = crud.get_session_by_id(db, session_id, include_deliverable=False)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )

    deliverable = crud.get_deliverable_by_session(db, session_id)
    if not deliverable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No deliverable found for session '{session_id}'"
        )
    return deliverable


@router.post("/sessions/{session_id}/deliverable", response_model=PlanningDeliverable, status_code=status.HTTP_201_CREATED)
def create_deliverable(
    session_id: str,
    deliverable_data: PlanningDeliverableCreate,
    db: Session = Depends(get_db)
):
    """
    Create a deliverable for a planning session.

    Called when the PAORT cycle completes with a structured plan.
    """
    # Verify session exists
    session = crud.get_session_by_id(db, session_id, include_deliverable=False)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning session '{session_id}' not found"
        )

    # Check for existing deliverable
    existing = crud.get_deliverable_by_session(db, session_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deliverable already exists for session '{session_id}'"
        )

    deliverable = crud.create_deliverable(db, session_id, deliverable_data)
    return deliverable


# ═══════════════════════════════════════════════════════════════════════════════
# Operational Memory
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/summary", response_model=OperationalMemorySummary)
def get_operational_memory_summary(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of recent sessions"),
    db: Session = Depends(get_db)
):
    """
    Get operational memory summary for planning context.

    Used by forge-smithy to provide continuity across planning sessions.
    Returns recent completed sessions and statistics.
    """
    stats = crud.get_session_stats(db, user_id=user_id)
    recent = crud.get_recent_session_summaries(db, user_id=user_id, limit=limit)

    # Convert to summary format
    recent_sessions = [
        PlanningSessionSummary(
            id=s["id"],
            user_id=user_id,
            status=SessionStatus.COMPLETED,
            request_title=s["title"],
            created_at=s["completed_at"],  # Use completed_at as created_at for summaries
            completed_at=s["completed_at"],
            has_deliverable=s["has_deliverable"]
        )
        for s in recent
    ]

    return OperationalMemorySummary(
        recent_sessions=recent_sessions,
        total_completed=stats["completed"],
        total_failed=stats["failed"],
        common_themes=[],  # TODO: Extract themes from session titles
        last_session_at=stats["last_session_at"]
    )
