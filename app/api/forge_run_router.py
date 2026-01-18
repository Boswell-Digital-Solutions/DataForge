"""
DataForge - ForgeAgents Run Persistence Router

Handles persistence of run execution records from ForgeAgents.
Writes to execution_index (fast queries) and run_evidence (full document).

Design Principles:
- DataForge owns all durable state (ForgeAgents is stateless beyond a run)
- Write both tables atomically in a single transaction
- Handle system_fault partial persistence (index row without evidence)
- True idempotency: same run_id + same evidence_hash = 200 OK, different hash = 409 Conflict
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.models import ExecutionIndex, RunEvidence
from app.models.forge_run_schemas import (
    PersistRunRequest,
    PersistRunResponse,
    ExecutionIndexResponse,
    RunEvidenceResponse,
    RunDetailResponse,
    ListRunsResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/forge-run",
    tags=["ForgeRun Persistence"],
)


# =============================================================================
# Persistence Endpoints
# =============================================================================

@router.post(
    "/persist",
    status_code=201,
    response_model=PersistRunResponse,
    summary="Persist run execution",
    description="""
    Persist a ForgeAgents run execution to DataForge.

    Called by ForgeAgents on run completion. Atomically writes to:
    - execution_index: Denormalized fields for fast /history queries
    - run_evidence: Full RunEvidence.v1 document as JSONB

    For system_fault cases, run_evidence may be omitted (partial persistence).

    Returns 409 Conflict if run_id already exists (idempotent).
    """
)
async def persist_run(
    request: PersistRunRequest,
    db: Session = Depends(get_db)
):
    """Persist run execution data."""
    try:
        run_id = request.execution_index.run_id
        logger.info(
            f"Persisting run {run_id}, final_status={request.execution_index.final_status}"
        )

        # Check for existing record - implement true idempotency
        existing = db.query(ExecutionIndex).filter(
            ExecutionIndex.run_id == run_id
        ).first()

        if existing:
            # True idempotency: same payload = success, different payload = conflict
            incoming_hash = request.execution_index.evidence_hash
            existing_hash = existing.evidence_hash

            if incoming_hash == existing_hash:
                # Idempotent success - same run, same content → 200 OK (not 201)
                logger.info(f"Run {run_id} already persisted (idempotent retry)")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "exists",
                        "run_id": run_id,
                        "message": f"Run {run_id} already persisted (idempotent)"
                    }
                )
            else:
                # Real conflict - same run_id but different content
                logger.warning(
                    f"Run {run_id} conflict: existing_hash={existing_hash}, "
                    f"incoming_hash={incoming_hash}"
                )
                raise HTTPException(
                    status_code=409,
                    detail=f"Run {run_id} already exists with different evidence hash"
                )

        # Create execution_index record
        index_data = request.execution_index.model_dump()

        # Parse timestamps if provided as strings
        if index_data.get("created_at") and isinstance(index_data["created_at"], str):
            try:
                index_data["created_at"] = datetime.fromisoformat(
                    index_data["created_at"].replace("Z", "+00:00")
                )
            except ValueError:
                index_data["created_at"] = None

        if index_data.get("completed_at") and isinstance(index_data["completed_at"], str):
            try:
                index_data["completed_at"] = datetime.fromisoformat(
                    index_data["completed_at"].replace("Z", "+00:00")
                )
            except ValueError:
                index_data["completed_at"] = datetime.now(timezone.utc)
        elif not index_data.get("completed_at"):
            index_data["completed_at"] = datetime.now(timezone.utc)

        # Rename 'metadata' to 'run_metadata' (SQLAlchemy reserves 'metadata')
        if "metadata" in index_data:
            index_data["run_metadata"] = index_data.pop("metadata")

        index_record = ExecutionIndex(**index_data)
        db.add(index_record)

        # Create run_evidence record if provided
        if request.run_evidence:
            evidence_data = request.run_evidence.model_dump()
            evidence_record = RunEvidence(**evidence_data)
            db.add(evidence_record)

        # Commit transaction
        db.commit()

        logger.info(
            f"Run {run_id} persisted successfully, "
            f"has_evidence={request.run_evidence is not None}"
        )

        return PersistRunResponse(
            status="created",
            run_id=run_id,
            message=f"Run {run_id} persisted successfully"
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error persisting run: {e}")
        raise HTTPException(
            status_code=409,
            detail="Run already exists or constraint violation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist run: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist run: {str(e)}"
        )


# =============================================================================
# Query Endpoints
# =============================================================================

@router.get(
    "/history",
    response_model=ListRunsResponse,
    summary="List run history",
    description="""
    Query run execution history with filters.

    Supports filtering by:
    - workflow_id, session_id
    - repo_id, branch
    - final_status
    - Date range

    Results sorted by created_at descending (most recent first).
    """
)
async def list_runs(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow"),
    session_id: Optional[str] = Query(None, description="Filter by session"),
    repo_id: Optional[str] = Query(None, description="Filter by repository"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    final_status: Optional[str] = Query(None, description="Filter by status"),
    promotion_ready: Optional[bool] = Query(None, description="Filter by promotion readiness"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List runs with filters."""
    try:
        query = db.query(ExecutionIndex)

        # Apply filters
        if workflow_id:
            query = query.filter(ExecutionIndex.workflow_id == workflow_id)
        if session_id:
            query = query.filter(ExecutionIndex.session_id == session_id)
        if repo_id:
            query = query.filter(ExecutionIndex.repo_id == repo_id)
        if branch:
            query = query.filter(ExecutionIndex.branch == branch)
        if final_status:
            query = query.filter(ExecutionIndex.final_status == final_status)
        if promotion_ready is not None:
            query = query.filter(ExecutionIndex.promotion_ready == promotion_ready)

        # Date filters
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(ExecutionIndex.created_at >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(ExecutionIndex.created_at <= end_dt)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        query = query.order_by(ExecutionIndex.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        runs = query.all()

        return ListRunsResponse(
            runs=[ExecutionIndexResponse.model_validate(r) for r in runs],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )

    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list runs: {str(e)}"
        )


@router.get(
    "/{run_id}",
    response_model=RunDetailResponse,
    summary="Get run details",
    description="Get full details of a specific run including evidence"
)
async def get_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Get details of a specific run."""
    try:
        index = db.query(ExecutionIndex).filter(
            ExecutionIndex.run_id == run_id
        ).first()

        if not index:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} not found"
            )

        evidence = db.query(RunEvidence).filter(
            RunEvidence.run_id == run_id
        ).first()

        return RunDetailResponse(
            index=ExecutionIndexResponse.model_validate(index),
            evidence=RunEvidenceResponse.model_validate(evidence) if evidence else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get run: {str(e)}"
        )


@router.get(
    "/{run_id}/evidence",
    response_model=RunEvidenceResponse,
    summary="Get run evidence",
    description="Get the full RunEvidence.v1 document for a run"
)
async def get_run_evidence(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Get evidence document for a run."""
    try:
        evidence = db.query(RunEvidence).filter(
            RunEvidence.run_id == run_id
        ).first()

        if not evidence:
            raise HTTPException(
                status_code=404,
                detail=f"Evidence for run {run_id} not found"
            )

        return RunEvidenceResponse.model_validate(evidence)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence for {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get evidence: {str(e)}"
        )


# =============================================================================
# Health Check
# =============================================================================

@router.get(
    "/health",
    summary="Health check"
)
async def health_check():
    """Health check for forge-run service."""
    return {
        "status": "healthy",
        "service": "dataforge-forge-run",
        "version": "1.0.0"
    }
