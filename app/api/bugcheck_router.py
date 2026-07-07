"""BugCheck API Router.

Provides persistence endpoints for BugCheck runs, findings, enrichments,
and lifecycle events. DataForge is the single source of truth.

API Endpoints:
- POST /api/v1/bugcheck/runs - Create a run
- GET /api/v1/bugcheck/runs/{run_id} - Get a run
- PATCH /api/v1/bugcheck/runs/{run_id} - Update a run
- POST /api/v1/bugcheck/runs/{run_id}/findings - Write a finding
- POST /api/v1/bugcheck/runs/{run_id}/findings/batch - Write findings batch
- GET /api/v1/bugcheck/runs/{run_id}/findings - Get findings for a run
- POST /api/v1/bugcheck/runs/{run_id}/progress - Write progress event
- POST /api/v1/bugcheck/findings/{finding_id}/enrichments - Write enrichment
- POST /api/v1/bugcheck/findings/{finding_id}/lifecycle - Write lifecycle event
"""

import logging
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import OperationalError
from app.models.bugcheck_models import (
    BugCheckRunModel,
    BugCheckFindingModel,
    BugCheckEnrichmentModel,
    BugCheckLifecycleEventModel,
    BugCheckProgressModel,
)
from app.models.bugcheck_schemas import (
    BugCheckRunCreate,
    BugCheckRunUpdate,
    BugCheckRunResponse,
    FindingCreate,
    FindingResponse,
    FindingsBatchResponse,
    EnrichmentCreate,
    EnrichmentResponse,
    LifecycleEventCreate,
    LifecycleEventResponse,
    ProgressEventCreate,
    ProgressEventResponse,
    RunStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/bugcheck",
    tags=["BugCheck"],
)


# ============================================================================
# Helper Functions
# ============================================================================


def verify_token(authorization: str | None) -> str:
    """Extract and verify bearer token.

    For now, just extract the token. In production, this would verify
    against ForgeCommand's token service.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    return authorization[7:]  # Strip "Bearer "


# ============================================================================
# Run Endpoints
# ============================================================================


@router.post(
    "/runs",
    status_code=201,
    response_model=BugCheckRunResponse,
    summary="Create a BugCheck run",
)
async def create_run(
    run: BugCheckRunCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Create a new BugCheck run record."""
    token = verify_token(authorization)

    logger.info(f"Creating BugCheck run {run.run_id}")

    # Check for duplicate
    existing = db.query(BugCheckRunModel).filter(
        BugCheckRunModel.id == run.run_id
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Run already exists")

    # Handle gating_result - convert enum to string if needed
    gating_result = run.gating_result
    if hasattr(gating_result, 'value'):
        gating_result = gating_result.value

    # Create model
    db_run = BugCheckRunModel(
        id=run.run_id,
        run_type=run.run_type.value,
        targets=run.targets,
        mode=run.mode.value,
        scope=run.scope.value,
        commit_sha=run.commit_sha,
        base_commit_sha=run.base_commit_sha,
        status=run.status.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        severity_counts=run.severity_counts.model_dump(),
        gating_result=gating_result,
        is_baseline=run.is_baseline,
        baseline_run_id=run.baseline_run_id,
        triggered_by=run.triggered_by,
        trigger_ref=run.trigger_ref,
        runtime_ms=run.runtime_ms,
        checks_run=run.checks_run,
        error_message=run.error_message,
        extra_metadata=run.metadata,
    )

    db.add(db_run)
    db.commit()
    db.refresh(db_run)

    logger.info(f"Created BugCheck run {run.run_id}")

    return _run_to_response(db_run)


@router.get(
    "/runs/{run_id}",
    response_model=BugCheckRunResponse,
    summary="Get a BugCheck run",
)
async def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a BugCheck run by ID."""
    db_run = db.query(BugCheckRunModel).filter(
        BugCheckRunModel.id == run_id
    ).first()

    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")

    return _run_to_response(db_run)


@router.get(
    "/runs",
    response_model=list[BugCheckRunResponse],
    summary="List BugCheck runs",
)
async def list_runs(
    limit: int = Query(20, ge=1, le=100, description="Max runs to return"),
    status: Optional[str] = Query(None, description="Filter by run status"),
    target: Optional[str] = Query(None, description="Filter by target service"),
    db: Session = Depends(get_db),
):
    """List recent BugCheck runs, newest first.

    Runs are ordered by ``started_at`` descending. ``status`` filters at the
    database level; ``target`` filters by membership in the run's target list
    (stored as JSON), applied over a bounded scan so ``limit`` still bounds the
    result set.
    """
    query = db.query(BugCheckRunModel)

    if status:
        query = query.filter(BugCheckRunModel.status == status)

    query = query.order_by(BugCheckRunModel.started_at.desc())

    if target:
        # targets is a JSON array; membership isn't portably expressible in SQL
        # across SQLite/Postgres, so filter in Python over a bounded scan.
        db_runs = []
        for db_run in query.limit(limit * 20).all():
            if target in (db_run.targets or []):
                db_runs.append(db_run)
                if len(db_runs) >= limit:
                    break
    else:
        db_runs = query.limit(limit).all()

    return [_run_to_response(db_run) for db_run in db_runs]


@router.patch(
    "/runs/{run_id}",
    status_code=200,
    response_model=BugCheckRunResponse,
    summary="Update a BugCheck run",
)
async def update_run(
    run_id: UUID,
    update: BugCheckRunUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Update a BugCheck run (status, severity counts, etc.)."""
    token = verify_token(authorization)

    db_run = db.query(BugCheckRunModel).filter(
        BugCheckRunModel.id == run_id
    ).first()

    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Apply updates
    if update.status is not None:
        db_run.status = update.status.value if hasattr(update.status, 'value') else update.status

    if update.completed_at is not None:
        if isinstance(update.completed_at, str):
            db_run.completed_at = datetime.fromisoformat(update.completed_at.replace('Z', '+00:00'))
        else:
            db_run.completed_at = update.completed_at

    if update.severity_counts is not None:
        if hasattr(update.severity_counts, 'model_dump'):
            db_run.severity_counts = update.severity_counts.model_dump()
        else:
            db_run.severity_counts = update.severity_counts

    if update.gating_result is not None:
        gating_result = update.gating_result
        if hasattr(gating_result, 'value'):
            gating_result = gating_result.value
        db_run.gating_result = gating_result

    if update.runtime_ms is not None:
        db_run.runtime_ms = update.runtime_ms

    if update.checks_run is not None:
        db_run.checks_run = update.checks_run

    if update.error_message is not None:
        db_run.error_message = update.error_message

    db.commit()
    db.refresh(db_run)

    logger.info(f"Updated BugCheck run {run_id}")

    return _run_to_response(db_run)


# ============================================================================
# Finding Endpoints
# ============================================================================


@router.post(
    "/runs/{run_id}/findings",
    status_code=201,
    response_model=FindingResponse,
    summary="Write a finding",
)
async def create_finding(
    run_id: UUID,
    finding: FindingCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Write a finding to a run."""
    token = verify_token(authorization)

    # Verify run exists and is not finalized
    db_run = db.query(BugCheckRunModel).filter(
        BugCheckRunModel.id == run_id
    ).first()

    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")

    if db_run.status == "finalized":
        # CRITICAL RULE #6: after FINALIZED, reject new findings with 409.
        raise OperationalError(
            status_code=409,
            code="RUN_ALREADY_FINALIZED",
            safe_message="Run is finalized",
        )

    # Check for duplicate
    existing = db.query(BugCheckFindingModel).filter(
        BugCheckFindingModel.id == finding.finding_id
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Finding already exists")

    # Create finding
    db_finding = BugCheckFindingModel(
        id=finding.finding_id,
        run_id=run_id,
        fingerprint=finding.fingerprint,
        correlation_id=finding.correlation_id,
        severity=finding.severity.value,
        category=finding.category.value,
        confidence=finding.confidence,
        title=finding.title,
        description=finding.description,
        location=finding.location.model_dump(),
        lifecycle_state=finding.lifecycle_state.value,
        autofix_available=finding.autofix_available,
        provenance=finding.provenance,
        rule_id=finding.rule_id,
        suggested_fix=finding.suggested_fix,
        related_docs=finding.related_docs,
        tags=finding.tags,
        first_seen_run_id=finding.first_seen_run_id,
        created_at=finding.created_at,
    )

    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)

    logger.debug(f"Created finding {finding.finding_id} for run {run_id}")

    return _finding_to_response(db_finding)


@router.post(
    "/runs/{run_id}/findings/batch",
    status_code=201,
    response_model=FindingsBatchResponse,
    summary="Write findings batch",
)
async def create_findings_batch(
    run_id: UUID,
    findings: list[FindingCreate],
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Write multiple findings in a batch."""
    token = verify_token(authorization)

    # Verify run exists and is not finalized
    db_run = db.query(BugCheckRunModel).filter(
        BugCheckRunModel.id == run_id
    ).first()

    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")

    if db_run.status == "finalized":
        # CRITICAL RULE #6: after FINALIZED, reject new findings with 409.
        raise OperationalError(
            status_code=409,
            code="RUN_ALREADY_FINALIZED",
            safe_message="Run is finalized",
        )

    count = 0
    for finding in findings:
        # Skip duplicates
        existing = db.query(BugCheckFindingModel).filter(
            BugCheckFindingModel.id == finding.finding_id
        ).first()

        if existing:
            continue

        db_finding = BugCheckFindingModel(
            id=finding.finding_id,
            run_id=run_id,
            fingerprint=finding.fingerprint,
            correlation_id=finding.correlation_id,
            severity=finding.severity.value,
            category=finding.category.value,
            confidence=finding.confidence,
            title=finding.title,
            description=finding.description,
            location=finding.location.model_dump(),
            lifecycle_state=finding.lifecycle_state.value,
            autofix_available=finding.autofix_available,
            provenance=finding.provenance,
            rule_id=finding.rule_id,
            suggested_fix=finding.suggested_fix,
            related_docs=finding.related_docs,
            tags=finding.tags,
            first_seen_run_id=finding.first_seen_run_id,
            created_at=finding.created_at,
        )

        db.add(db_finding)
        count += 1

    db.commit()

    logger.info(f"Created {count} findings for run {run_id}")

    return FindingsBatchResponse(count=count)


@router.get(
    "/runs/{run_id}/findings",
    response_model=list[FindingResponse],
    summary="Get findings for a run",
)
async def get_findings(
    run_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get findings for a run."""
    findings = db.query(BugCheckFindingModel).filter(
        BugCheckFindingModel.run_id == run_id
    ).offset(offset).limit(limit).all()

    return [_finding_to_response(f) for f in findings]


# ============================================================================
# Progress Endpoints
# ============================================================================


@router.post(
    "/runs/{run_id}/progress",
    status_code=201,
    summary="Write progress event",
)
async def create_progress(
    run_id: UUID,
    event: ProgressEventCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Write a progress event for WebSocket streaming."""
    token = verify_token(authorization)

    # Parse timestamp if string
    timestamp = event.timestamp
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    db_progress = BugCheckProgressModel(
        run_id=run_id,
        event_type=event.event_type,
        message=event.message,
        extra_metadata=event.metadata,
        timestamp=timestamp,
    )

    db.add(db_progress)
    db.commit()

    return {"status": "ok"}


# ============================================================================
# Enrichment Endpoints
# ============================================================================


@router.post(
    "/findings/{finding_id}/enrichments",
    status_code=201,
    response_model=EnrichmentResponse,
    summary="Write enrichment",
)
async def create_enrichment(
    finding_id: UUID,
    enrichment: EnrichmentCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Write an enrichment to a finding."""
    token = verify_token(authorization)

    # Verify finding exists
    db_finding = db.query(BugCheckFindingModel).filter(
        BugCheckFindingModel.id == finding_id
    ).first()

    if not db_finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    db_enrichment = BugCheckEnrichmentModel(
        id=enrichment.enrichment_id,
        finding_id=finding_id,
        source=enrichment.source.value,
        version=enrichment.version,
        enrichment_type=enrichment.enrichment_type.value if enrichment.enrichment_type else None,
        content=enrichment.content.model_dump(),
        confidence=enrichment.confidence,
        status=enrichment.status.value,
        reviewed_by=enrichment.reviewed_by,
        reviewed_at=enrichment.reviewed_at,
        rejection_reason=enrichment.rejection_reason,
        model_used=enrichment.model_used,
        tokens_used=enrichment.tokens_used,
        latency_ms=enrichment.latency_ms,
        created_at=enrichment.created_at,
    )

    db.add(db_enrichment)
    db.commit()
    db.refresh(db_enrichment)

    return _enrichment_to_response(db_enrichment)


# ============================================================================
# Lifecycle Endpoints
# ============================================================================


@router.post(
    "/findings/{finding_id}/lifecycle",
    status_code=201,
    response_model=LifecycleEventResponse,
    summary="Write lifecycle event",
)
async def create_lifecycle_event(
    finding_id: UUID,
    event: LifecycleEventCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Write a lifecycle transition event."""
    token = verify_token(authorization)

    # Verify finding exists
    db_finding = db.query(BugCheckFindingModel).filter(
        BugCheckFindingModel.id == finding_id
    ).first()

    if not db_finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Validate state transition
    current_state = db_finding.lifecycle_state
    if current_state != event.from_state.value:
        raise OperationalError(
            status_code=409,
            code="INVALID_LIFECYCLE_TRANSITION",
            safe_message=f"Invalid transition: finding is in state {current_state}, not {event.from_state.value}",
        )

    db_event = BugCheckLifecycleEventModel(
        id=event.event_id,
        finding_id=finding_id,
        from_state=event.from_state.value,
        to_state=event.to_state.value,
        actor_type=event.actor.type.value,
        actor_id=event.actor.id,
        actor_name=event.actor.name,
        reason=event.reason,
        scope=event.scope.value if event.scope else None,
        expires_at=event.expires_at,
        enrichment_id=event.enrichment_id,
        extra_metadata=event.metadata,
        timestamp=event.timestamp,
    )

    db.add(db_event)

    # Update finding state
    db_finding.lifecycle_state = event.to_state.value
    db_finding.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(db_event)

    return _lifecycle_event_to_response(db_event)


# ============================================================================
# Response Helpers
# ============================================================================


def _run_to_response(db_run: BugCheckRunModel) -> BugCheckRunResponse:
    """Convert database model to response schema."""
    return BugCheckRunResponse(
        run_id=db_run.id,
        run_type=db_run.run_type,
        targets=db_run.targets,
        mode=db_run.mode,
        scope=db_run.scope,
        commit_sha=db_run.commit_sha,
        base_commit_sha=db_run.base_commit_sha,
        status=db_run.status,
        started_at=db_run.started_at,
        completed_at=db_run.completed_at,
        severity_counts=db_run.severity_counts,
        gating_result=db_run.gating_result,
        is_baseline=db_run.is_baseline,
        baseline_run_id=db_run.baseline_run_id,
        triggered_by=db_run.triggered_by,
        trigger_ref=db_run.trigger_ref,
        runtime_ms=db_run.runtime_ms,
        checks_run=db_run.checks_run,
        error_message=db_run.error_message,
        metadata=db_run.extra_metadata,
    )


def _finding_to_response(db_finding: BugCheckFindingModel) -> FindingResponse:
    """Convert database model to response schema."""
    return FindingResponse(
        finding_id=db_finding.id,
        run_id=db_finding.run_id,
        fingerprint=db_finding.fingerprint,
        correlation_id=db_finding.correlation_id,
        severity=db_finding.severity,
        category=db_finding.category,
        confidence=db_finding.confidence,
        title=db_finding.title,
        description=db_finding.description,
        location=db_finding.location,
        lifecycle_state=db_finding.lifecycle_state,
        autofix_available=db_finding.autofix_available,
        provenance=db_finding.provenance,
        rule_id=db_finding.rule_id,
        suggested_fix=db_finding.suggested_fix,
        related_docs=db_finding.related_docs,
        tags=db_finding.tags,
        first_seen_run_id=db_finding.first_seen_run_id,
        created_at=db_finding.created_at,
        updated_at=db_finding.updated_at,
    )


def _enrichment_to_response(db_enrichment: BugCheckEnrichmentModel) -> EnrichmentResponse:
    """Convert database model to response schema."""
    return EnrichmentResponse(
        enrichment_id=db_enrichment.id,
        finding_id=db_enrichment.finding_id,
        source=db_enrichment.source,
        version=db_enrichment.version,
        enrichment_type=db_enrichment.enrichment_type,
        content=db_enrichment.content,
        confidence=db_enrichment.confidence,
        status=db_enrichment.status,
        reviewed_by=db_enrichment.reviewed_by,
        reviewed_at=db_enrichment.reviewed_at,
        rejection_reason=db_enrichment.rejection_reason,
        model_used=db_enrichment.model_used,
        tokens_used=db_enrichment.tokens_used,
        latency_ms=db_enrichment.latency_ms,
        created_at=db_enrichment.created_at,
    )


def _lifecycle_event_to_response(db_event: BugCheckLifecycleEventModel) -> LifecycleEventResponse:
    """Convert database model to response schema."""
    return LifecycleEventResponse(
        event_id=db_event.id,
        finding_id=db_event.finding_id,
        from_state=db_event.from_state,
        to_state=db_event.to_state,
        actor_type=db_event.actor_type,
        actor_id=db_event.actor_id,
        actor_name=db_event.actor_name,
        reason=db_event.reason,
        scope=db_event.scope,
        expires_at=db_event.expires_at,
        enrichment_id=db_event.enrichment_id,
        metadata=db_event.extra_metadata,
        timestamp=db_event.timestamp,
    )
