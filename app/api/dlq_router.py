"""
Dead Letter Queue Management API Routes

Admin endpoints for monitoring, managing, and recovering from failed tasks.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.utils.dead_letter_queue import get_dlq, DLQItemStatus
from app.utils.task_retry_policy import get_retry_policy_registry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/dlq",
    tags=["Dead Letter Queue"],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}},
)


# ============================================
# Pydantic Models
# ============================================

class DLQItemResponse(BaseModel):
    """Response model for DLQ item."""
    id: str
    task_name: str
    task_id: str
    exception: str
    status: str
    retry_count: int
    max_retries: int
    created_at: str
    last_retry_at: Optional[str]
    next_retry_at: Optional[str]
    notes: str
    priority: int
    error_history: List[Dict[str, str]]

    class Config:
        from_attributes = True


class DLQMetricsResponse(BaseModel):
    """Response model for DLQ metrics."""
    total_items: int
    failed_items: int
    retrying_items: int
    permanently_failed_items: int
    resolved_items: int
    avg_retry_count: float
    last_updated: str


class DLQListResponse(BaseModel):
    """Response model for listing DLQ items."""
    items: List[DLQItemResponse]
    total: int
    limit: int
    offset: int


class DLQActionRequest(BaseModel):
    """Request model for DLQ actions."""
    action: str  # "retry", "mark_failed", "resolve"
    notes: Optional[str] = None


class DLQTaskStatusResponse(BaseModel):
    """Response model for task status in DLQ."""
    task_name: str
    failed: int
    retrying: int
    permanently_failed: int
    resolved: int


# ============================================
# Health & Status Endpoints
# ============================================

@router.get("/health", response_model=Dict[str, Any])
async def dlq_health():
    """Check DLQ health status."""
    dlq = get_dlq()
    metrics = dlq.get_metrics()
    
    # Determine health status
    if metrics.permanently_failed_items > 100:
        status = "warning"
    elif metrics.permanently_failed_items > 500:
        status = "critical"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "dlq_items": metrics.total_items,
        "permanently_failed": metrics.permanently_failed_items,
        "retrying": metrics.retrying_items,
        "message": f"DLQ has {metrics.total_items} items"
    }


@router.get("/metrics", response_model=DLQMetricsResponse)
async def get_dlq_metrics():
    """Get comprehensive DLQ metrics."""
    dlq = get_dlq()
    metrics = dlq.get_metrics()
    
    return DLQMetricsResponse(
        total_items=metrics.total_items,
        failed_items=metrics.failed_items,
        retrying_items=metrics.retrying_items,
        permanently_failed_items=metrics.permanently_failed_items,
        resolved_items=metrics.resolved_items,
        avg_retry_count=metrics.avg_retry_count,
        last_updated=metrics.last_updated,
    )


@router.get("/status/by-task", response_model=Dict[str, DLQTaskStatusResponse])
async def get_dlq_status_by_task():
    """Get DLQ status broken down by task type."""
    dlq = get_dlq()
    status_map = dlq.get_status_by_task()
    
    result = {}
    for task_name, counts in status_map.items():
        result[task_name] = DLQTaskStatusResponse(
            task_name=task_name,
            failed=counts.get("failed", 0),
            retrying=counts.get("retrying", 0),
            permanently_failed=counts.get("permanently_failed", 0),
            resolved=counts.get("resolved", 0),
        )
    
    return result


# ============================================
# List & Query Endpoints
# ============================================

@router.get("/items", response_model=DLQListResponse)
async def list_dlq_items(
    status: Optional[str] = Query(None),
    task_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List DLQ items with optional filtering."""
    dlq = get_dlq()
    
    # Convert status string to enum
    status_enum = None
    if status:
        try:
            status_enum = DLQItemStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in DLQItemStatus]}"
            )
    
    items, total = dlq.get_all_items(
        status=status_enum,
        task_name=task_name,
        limit=limit,
        offset=offset
    )
    
    return DLQListResponse(
        items=[DLQItemResponse(**item.to_dict()) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/items/{dlq_item_id}", response_model=DLQItemResponse)
async def get_dlq_item(dlq_item_id: str):
    """Get a specific DLQ item by ID."""
    dlq = get_dlq()
    item = dlq.get_item(dlq_item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="DLQ item not found")
    
    return DLQItemResponse(**item.to_dict())


@router.get("/items-for-retry", response_model=DLQListResponse)
async def get_items_for_retry(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get items ready for retry (past their next_retry_at time)."""
    dlq = get_dlq()
    all_items = dlq.get_items_for_retry()
    
    total = len(all_items)
    items = all_items[offset:offset + limit]
    
    return DLQListResponse(
        items=[DLQItemResponse(**item.to_dict()) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================
# Action Endpoints
# ============================================

@router.post("/items/{dlq_item_id}/retry")
async def retry_dlq_item(dlq_item_id: str):
    """Mark a DLQ item for retry."""
    dlq = get_dlq()
    
    success = dlq.mark_retrying(dlq_item_id)
    if not success:
        raise HTTPException(status_code=404, detail="DLQ item not found")
    
    item = dlq.get_item(dlq_item_id)
    return {
        "status": "success",
        "message": f"Item marked for retry. Next retry at: {item.next_retry_at}",
        "item": DLQItemResponse(**item.to_dict()),
    }


@router.post("/items/{dlq_item_id}/mark-failed")
async def mark_dlq_item_failed(
    dlq_item_id: str,
    reason: str = Query(""),
):
    """Mark a DLQ item as permanently failed."""
    dlq = get_dlq()
    
    success = dlq.mark_permanently_failed(dlq_item_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="DLQ item not found")
    
    item = dlq.get_item(dlq_item_id)
    return {
        "status": "success",
        "message": "Item marked as permanently failed",
        "item": DLQItemResponse(**item.to_dict()),
    }


@router.post("/items/{dlq_item_id}/resolve")
async def resolve_dlq_item(
    dlq_item_id: str,
    notes: str = Query(""),
):
    """Mark a DLQ item as resolved (manual intervention applied)."""
    dlq = get_dlq()
    
    success = dlq.mark_resolved(dlq_item_id, notes)
    if not success:
        raise HTTPException(status_code=404, detail="DLQ item not found")
    
    item = dlq.get_item(dlq_item_id)
    return {
        "status": "success",
        "message": "Item marked as resolved",
        "item": DLQItemResponse(**item.to_dict()),
    }


# ============================================
# Cleanup Endpoints
# ============================================

@router.delete("/cleanup/resolved")
async def cleanup_resolved_items(days_old: int = Query(7, ge=1)):
    """Clean up resolved items older than specified days."""
    dlq = get_dlq()
    count = dlq.cleanup_resolved_items(days_old)
    
    return {
        "status": "success",
        "message": f"Cleaned up {count} resolved items older than {days_old} days",
        "count": count,
    }


@router.post("/retry/batch")
async def batch_retry_failed_items(
    max_retries: int = Query(3, ge=1, le=5),
    task_name: Optional[str] = Query(None),
):
    """Retry multiple failed items at once."""
    dlq = get_dlq()
    items, _ = dlq.get_all_items(
        status=DLQItemStatus.FAILED,
        task_name=task_name,
        limit=1000
    )
    
    retried_count = 0
    for item in items:
        if item.retry_count < max_retries:
            dlq.mark_retrying(item.id)
            retried_count += 1
    
    return {
        "status": "success",
        "message": f"Retried {retried_count} items",
        "count": retried_count,
    }


# ============================================
# Policy Endpoints
# ============================================

@router.get("/policies", response_model=Dict[str, Dict[str, Any]])
async def get_all_policies():
    """Get all task retry policies."""
    registry = get_retry_policy_registry()
    return registry.get_all_policies()


@router.get("/policies/{task_name}", response_model=Dict[str, Any])
async def get_task_policy(task_name: str):
    """Get retry policy for a specific task."""
    registry = get_retry_policy_registry()
    policy = registry.get_policy(task_name)
    
    return {
        "task_name": task_name,
        "policy": policy.to_dict(),
    }


# ============================================
# Export Endpoints
# ============================================

@router.get("/export/json")
async def export_dlq_json():
    """Export all DLQ items as JSON."""
    dlq = get_dlq()
    json_str = dlq.export_to_json()
    
    return {
        "status": "success",
        "data": json_str,
        "message": f"Exported {dlq.get_metrics().total_items} DLQ items",
    }
