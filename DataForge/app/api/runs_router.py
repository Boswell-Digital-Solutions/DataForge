"""
DataForge - Run History & Analytics Router

Handles storage and retrieval of prompt execution runs from VibeForge/NeuroForge.
Provides analytics and metrics over run history.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.runs_service import RunsService
from app.models.runs_schemas import (
    RunCreate, RunSummary, ListRunsResponse, UsageMetrics,
    RunDetailResponse, DeleteRunResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/runs",
    tags=["Runs & Analytics"],
)


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "",
    status_code=201,
    summary="Log a run",
    description="""
    Log a prompt execution run to DataForge for analytics and history.
    
    Called by NeuroForge after successful execution.
    Stores full execution details including:
    - Prompt snapshot
    - Context blocks used
    - Results from all models
    - Token usage and costs
    - Timing information
    """
)
async def log_run(
    request: RunCreate,
    db: Session = Depends(get_db)
):
    """Log a run to the database."""
    try:
        logger.info(
            f"Logging run {request.run_id} for workspace {request.workspace_id}"
        )
        
        service = RunsService(db)
        result = service.log_run(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to log run {request.run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log run: {str(e)}"
        )


@router.get(
    "",
    response_model=ListRunsResponse,
    summary="List runs",
    description="""
    List runs with optional filters.
    
    Supports filtering by:
    - Workspace ID
    - Model ID
    - Status
    - Date range
    - Tags
    
    Returns paginated results with summary information.
    """
)
async def list_runs(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace"),
    model_id: Optional[str] = Query(None, description="Filter by model"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List runs with filters."""
    try:
        logger.info(
            f"Listing runs: workspace={workspace_id}, model={model_id}, "
            f"page={page}, page_size={page_size}"
        )
        
        # Parse tags
        tags_list = tags.split(",") if tags else None
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        service = RunsService(db)
        result = service.list_runs(
            workspace_id=workspace_id,
            model_id=model_id,
            status=status,
            tags=tags_list,
            start_date=start_dt,
            end_date=end_dt,
            page=page,
            page_size=page_size
        )
        
        return result
        
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
    description="Get detailed information about a specific run"
)
async def get_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Get details of a specific run."""
    try:
        logger.info(f"Fetching run {run_id}")
        
        service = RunsService(db)
        result = service.get_run_details(run_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get run: {str(e)}"
        )


@router.delete(
    "/{run_id}",
    summary="Delete a run",
    description="Delete a run from history"
)
async def delete_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Delete a run."""
    try:
        logger.info(f"Deleting run {run_id}")
        
        service = RunsService(db)
        result = service.delete_run(run_id)
        
        if result.status == "error":
            raise HTTPException(
                status_code=404,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete run: {str(e)}"
        )


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get(
    "/analytics/usage",
    response_model=UsageMetrics,
    summary="Get usage metrics",
    description="""
    Get usage metrics for a workspace over a time period.
    
    Includes:
    - Total runs
    - Token usage
    - Costs
    - Breakdown by model
    """
)
async def get_usage_metrics(
    workspace_id: str = Query(..., description="Workspace ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db)
):
    """Get usage metrics for a workspace."""
    try:
        logger.info(f"Fetching usage metrics for workspace {workspace_id}")
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        service = RunsService(db)
        result = service.get_usage_metrics(
            workspace_id=workspace_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get usage metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage metrics: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check"
)
async def health_check():
    """Health check for runs service."""
    return {
        "status": "healthy",
        "service": "dataforge-runs",
        "version": "1.0.0"
    }
