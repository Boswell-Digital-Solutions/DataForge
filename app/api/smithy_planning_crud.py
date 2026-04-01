"""
Smithy Planning Session CRUD Operations

Database operations for Planning sessions, deliverables, and steps.
"""

from datetime import datetime, timedelta, UTC
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.models.smithy_planning_models import (
    SmithyPlanningSession,
    SmithyPlanningDeliverable,
    SmithyPlanningStep,
    SessionStatus,
)
from app.models.smithy_planning_schemas import (
    PlanningSessionCreate,
    PlanningSessionUpdate,
    PlanningDeliverableCreate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Planning Sessions
# ═══════════════════════════════════════════════════════════════════════════════

def get_sessions(
    db: Session,
    user_id: Optional[str] = None,
    status: Optional[SessionStatus] = None,
    limit: int = 50,
    offset: int = 0
) -> list[SmithyPlanningSession]:
    """Get planning sessions with optional filtering."""
    query = db.query(SmithyPlanningSession)

    if user_id:
        query = query.filter(SmithyPlanningSession.user_id == user_id)
    if status:
        query = query.filter(SmithyPlanningSession.status == status)

    return (
        query
        .order_by(desc(SmithyPlanningSession.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_session_by_id(
    db: Session,
    session_id: str,
    include_deliverable: bool = True
) -> Optional[SmithyPlanningSession]:
    """Get a planning session by ID."""
    query = db.query(SmithyPlanningSession)

    if include_deliverable:
        query = query.options(
            joinedload(SmithyPlanningSession.deliverable)
            .joinedload(SmithyPlanningDeliverable.steps)
        )

    return query.filter(SmithyPlanningSession.id == session_id).first()


def get_session_by_forgeagents_id(
    db: Session,
    forgeagents_session_id: str
) -> Optional[SmithyPlanningSession]:
    """Get a planning session by ForgeAgents session ID."""
    return (
        db.query(SmithyPlanningSession)
        .filter(SmithyPlanningSession.forgeagents_session_id == forgeagents_session_id)
        .first()
    )


def create_session(
    db: Session,
    session_data: PlanningSessionCreate
) -> SmithyPlanningSession:
    """Create a new planning session."""
    session = SmithyPlanningSession(
        user_id=session_data.user_id,
        forgeagents_session_id=session_data.forgeagents_session_id,
        status=SessionStatus.PENDING,
        request_title=session_data.request_title,
        request_description=session_data.request_description,
        request_repo_url=session_data.request_repo_url,
        request_repo_commit=session_data.request_repo_commit,
        normalized_prompt=session_data.normalized_prompt,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session(
    db: Session,
    session_id: str,
    update_data: PlanningSessionUpdate
) -> Optional[SmithyPlanningSession]:
    """Update an existing planning session."""
    session = db.query(SmithyPlanningSession).filter(
        SmithyPlanningSession.id == session_id
    ).first()

    if not session:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(session, key, value)

    db.commit()
    db.refresh(session)
    return session


def start_session(db: Session, session_id: str) -> Optional[SmithyPlanningSession]:
    """Mark a session as running."""
    return update_session(
        db,
        session_id,
        PlanningSessionUpdate(
            status=SessionStatus.RUNNING,
            started_at=datetime.now(UTC)
        )
    )


def complete_session(db: Session, session_id: str) -> Optional[SmithyPlanningSession]:
    """Mark a session as completed."""
    return update_session(
        db,
        session_id,
        PlanningSessionUpdate(
            status=SessionStatus.COMPLETED,
            completed_at=datetime.now(UTC)
        )
    )


def fail_session(
    db: Session,
    session_id: str,
    error_message: str,
    error_stage: Optional[str] = None
) -> Optional[SmithyPlanningSession]:
    """Mark a session as failed with error details."""
    return update_session(
        db,
        session_id,
        PlanningSessionUpdate(
            status=SessionStatus.FAILED,
            completed_at=datetime.now(UTC),
            error_message=error_message,
            error_stage=error_stage
        )
    )


def cancel_session(db: Session, session_id: str) -> Optional[SmithyPlanningSession]:
    """Mark a session as cancelled."""
    return update_session(
        db,
        session_id,
        PlanningSessionUpdate(
            status=SessionStatus.CANCELLED,
            completed_at=datetime.now(UTC)
        )
    )


def delete_session(db: Session, session_id: str) -> bool:
    """Delete a planning session and all related data."""
    session = db.query(SmithyPlanningSession).filter(
        SmithyPlanningSession.id == session_id
    ).first()

    if not session:
        return False

    db.delete(session)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Planning Deliverables
# ═══════════════════════════════════════════════════════════════════════════════

def get_deliverable_by_session(
    db: Session,
    session_id: str
) -> Optional[SmithyPlanningDeliverable]:
    """Get the deliverable for a session."""
    return (
        db.query(SmithyPlanningDeliverable)
        .options(joinedload(SmithyPlanningDeliverable.steps))
        .filter(SmithyPlanningDeliverable.session_id == session_id)
        .first()
    )


def create_deliverable(
    db: Session,
    session_id: str,
    deliverable_data: PlanningDeliverableCreate
) -> SmithyPlanningDeliverable:
    """Create a deliverable for a planning session."""
    # Create the deliverable
    deliverable = SmithyPlanningDeliverable(
        session_id=session_id,
        plan_title=deliverable_data.plan_title,
        plan_overview=deliverable_data.plan_overview,
        plan_estimated_effort=deliverable_data.plan_estimated_effort,
        plan_risks=deliverable_data.plan_risks,
        execution_prompt=deliverable_data.execution_prompt,
        total_tokens=deliverable_data.total_tokens,
        total_cost=deliverable_data.total_cost,
        duration_ms=deliverable_data.duration_ms,
        tone_violations=deliverable_data.tone_violations,
    )
    db.add(deliverable)
    db.flush()  # Get the deliverable ID

    # Create steps
    for step_data in deliverable_data.steps:
        step = SmithyPlanningStep(
            deliverable_id=deliverable.id,
            step_order=step_data.step_order,
            title=step_data.title,
            description=step_data.description,
            estimated_effort=step_data.estimated_effort,
            dependencies=step_data.dependencies,
            acceptance_criteria=step_data.acceptance_criteria,
        )
        db.add(step)

    db.commit()
    db.refresh(deliverable)
    return deliverable


# ═══════════════════════════════════════════════════════════════════════════════
# Operational Memory / Analytics
# ═══════════════════════════════════════════════════════════════════════════════

def get_session_stats(
    db: Session,
    user_id: Optional[str] = None,
    days: int = 30
) -> dict:
    """Get session statistics for operational memory."""
    since = datetime.now(UTC) - timedelta(days=days)

    query = db.query(SmithyPlanningSession).filter(
        SmithyPlanningSession.created_at >= since
    )

    if user_id:
        query = query.filter(SmithyPlanningSession.user_id == user_id)

    sessions = query.all()

    completed = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
    failed = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

    # Get last session timestamp
    last_session = (
        db.query(SmithyPlanningSession)
        .filter(SmithyPlanningSession.user_id == user_id if user_id else True)
        .order_by(desc(SmithyPlanningSession.created_at))
        .first()
    )

    return {
        "total_sessions": len(sessions),
        "completed": completed,
        "failed": failed,
        "success_rate": completed / len(sessions) if sessions else 0,
        "last_session_at": last_session.created_at if last_session else None,
    }


def get_recent_session_summaries(
    db: Session,
    user_id: Optional[str] = None,
    limit: int = 10
) -> list[dict]:
    """Get recent session summaries for operational memory context."""
    query = db.query(SmithyPlanningSession)

    if user_id:
        query = query.filter(SmithyPlanningSession.user_id == user_id)

    sessions = (
        query
        .filter(SmithyPlanningSession.status == SessionStatus.COMPLETED)
        .order_by(desc(SmithyPlanningSession.completed_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": s.id,
            "title": s.request_title,
            "completed_at": s.completed_at,
            "has_deliverable": s.deliverable is not None,
        }
        for s in sessions
    ]
