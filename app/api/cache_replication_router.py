"""
Cache Replication REST API Router

FastAPI router providing HTTP endpoints for:
    - Cache replication management (register, status, lag)
    - Failover orchestration (health, state, promotion)
    - Cache metrics and monitoring
    - Sentinel integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.utils.cache_replication import (
    get_cache_replication_manager,
    ReplicaConfig,
    ReplicaRole,
    ReplicationMode,
)
from app.utils.cache_failover import (
    get_cache_failover_manager,
    FailoverConfig,
    FailoverMode,
    FailoverReason,
)


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class ReplicaRegisterRequest(BaseModel):
    """Request to register a cache replica."""
    name: str = Field(..., description="Unique replica name")
    host: str = Field(..., description="Redis host address")
    port: int = Field(6379, description="Redis port")
    role: str = Field("replica", description="Replica role (replica, read_replica)")
    region: str = Field("primary", description="Geographic region")
    replication_mode: str = Field("asynchronous", description="Replication mode")
    slave_priority: int = Field(100, description="Promotion priority (higher = preferred)")


class ReplicaStatusResponse(BaseModel):
    """Response with replica status information."""
    name: str
    host: str
    port: int
    role: str
    region: str
    replication_mode: str
    status: str
    lag_ms: float
    offset: int
    registered_at: Optional[str]


class ReplicationMetricsResponse(BaseModel):
    """Response with replication metrics."""
    timestamp: str
    connected_replicas: int
    total_replicas: int
    replication_backlog_bytes: int
    average_lag_ms: float
    min_lag_ms: float
    max_lag_ms: float
    sync_in_progress: bool
    partial_resync_success: int


class FailoverStateResponse(BaseModel):
    """Response with current failover state."""
    state: str
    primary_host: str
    primary_port: int
    failover_mode: str
    health_check_interval: int
    failure_threshold: int
    failures_in_window: int
    last_health_check: Optional[str]
    readonly_mode: bool


class FailoverMetricsResponse(BaseModel):
    """Response with failover metrics."""
    current_state: str
    failover_count: int
    primary_failure_count: int
    health_check_failures: int
    last_failover_duration_seconds: float
    last_failover_reason: Optional[str]
    recovery_attempts: int


class PromoteReplicaRequest(BaseModel):
    """Request to promote a replica to primary."""
    replica_name: str = Field(..., description="Name of replica to promote")
    reason: str = Field("manual_initiation", description="Failover reason")


class SetReplicationModeRequest(BaseModel):
    """Request to change replication mode for a replica."""
    replica_name: str = Field(..., description="Target replica")
    mode: str = Field(..., description="Mode: asynchronous, synchronous, quorum")


class InitiateFailoverRequest(BaseModel):
    """Request to initiate failover."""
    reason: str = Field("manual_initiation", description="Failover reason")
    replica_name: Optional[str] = Field(None, description="Specific replica to promote")


class RecoverPrimaryRequest(BaseModel):
    """Request to recover old primary as replica."""
    primary_name: str = Field(..., description="Name of old primary to recover")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_replication_manager() -> Any:
    """Dependency: get cache replication manager."""
    return get_cache_replication_manager()


def get_failover_manager() -> Any:
    """Dependency: get cache failover manager."""
    return get_cache_failover_manager()


# ============================================================================
# Router Definition
# ============================================================================

router = APIRouter(prefix="/cache", tags=["cache-replication"])


# ============================================================================
# Health & Monitoring Endpoints
# ============================================================================

@router.get("/health")
async def get_health(
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """
    Get cache replication service health status.
    
    Returns:
        Health status with replica counts and metrics
    """
    try:
        connected = sum(
            1 for r in replication_mgr.replicas.values()
            if replication_mgr.check_replica_connectivity(r.name)
        )
        total = len(replication_mgr.replicas)
        
        return {
            "status": "healthy",
            "service": "cache-replication",
            "connected_replicas": connected,
            "total_replicas": total,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Get cache replication metrics."""
    try:
        return replication_mgr.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Replica Management Endpoints
# ============================================================================

@router.get("/replicas", response_model=Dict[str, List[ReplicaStatusResponse]])
async def list_replicas(
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, List[Dict[str, Any]]]:
    """List all registered cache replicas."""
    try:
        replicas = []
        for replica_name in replication_mgr.replicas:
            status = replication_mgr.get_replica_status(replica_name)
            if status:
                replicas.append(status)
        return {"replicas": replicas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replicas")
async def register_replica(
    request: ReplicaRegisterRequest,
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Register a new cache replica."""
    try:
        config = ReplicaConfig(
            name=request.name,
            host=request.host,
            port=request.port,
            role=ReplicaRole(request.role),
            region=request.region,
            replication_mode=ReplicationMode(request.replication_mode),
            slave_priority=request.slave_priority,
        )
        
        success = replication_mgr.register_replica(config)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to register replica")
        
        return {
            "status": "registered",
            "replica_name": request.name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replicas/{replica_name}", response_model=ReplicaStatusResponse)
async def get_replica_status(
    replica_name: str,
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Get status of a specific replica."""
    try:
        status = replication_mgr.get_replica_status(replica_name)
        if not status:
            raise HTTPException(status_code=404, detail="Replica not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/replicas/{replica_name}")
async def unregister_replica(
    replica_name: str,
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Unregister a cache replica."""
    try:
        success = replication_mgr.unregister_replica(replica_name)
        if not success:
            raise HTTPException(status_code=404, detail="Replica not found")
        
        return {
            "status": "unregistered",
            "replica_name": replica_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replicas/{replica_name}/lag")
async def get_replica_lag(
    replica_name: str,
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Get replication lag for a specific replica."""
    try:
        if replica_name not in replication_mgr.replicas:
            raise HTTPException(status_code=404, detail="Replica not found")
        
        lag_ms = replication_mgr.get_replica_lag_ms(replica_name)
        return {
            "replica_name": replica_name,
            "lag_ms": lag_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replicas/{replica_name}/sync-mode")
async def set_replication_mode(
    replica_name: str,
    request: SetReplicationModeRequest,
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Change replication mode for a replica."""
    try:
        mode = ReplicationMode(request.mode)
        success = replication_mgr.set_replication_mode(replica_name, mode)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to set replication mode")
        
        return {
            "status": "updated",
            "replica_name": replica_name,
            "mode": request.mode,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Replication Info Endpoints
# ============================================================================

@router.get("/replication-info")
async def get_replication_info(
    replication_mgr: Any = Depends(get_replication_manager)
) -> Dict[str, Any]:
    """Get comprehensive replication information."""
    try:
        return replication_mgr.get_replication_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Failover Endpoints
# ============================================================================

@router.get("/failover/state", response_model=FailoverStateResponse)
async def get_failover_state(
    failover_mgr: Any = Depends(get_failover_manager)
) -> Dict[str, Any]:
    """Get current failover state and configuration."""
    try:
        return failover_mgr.get_current_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failover/metrics", response_model=FailoverMetricsResponse)
async def get_failover_metrics(
    failover_mgr: Any = Depends(get_failover_manager)
) -> Dict[str, Any]:
    """Get failover metrics and statistics."""
    try:
        return failover_mgr.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/initiate")
async def initiate_failover(
    request: InitiateFailoverRequest,
    replication_mgr: Any = Depends(get_replication_manager),
    failover_mgr: Any = Depends(get_failover_manager)
) -> Dict[str, Any]:
    """Initiate manual cache failover."""
    try:
        reason = FailoverReason(request.reason)
        success = failover_mgr.initiate_failover(reason, request.replica_name)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failover initiation failed")
        
        return {
            "status": "failover_initiated",
            "reason": request.reason,
            "state": failover_mgr.metrics.current_state.value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid reason: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/promote/{replica_name}")
async def promote_replica(
    replica_name: str,
    request: PromoteReplicaRequest,
    replication_mgr: Any = Depends(get_replication_manager),
    failover_mgr: Any = Depends(get_failover_manager)
) -> Dict[str, Any]:
    """Manually promote a replica to primary."""
    try:
        reason = FailoverReason(request.reason)
        success = failover_mgr.initiate_failover(reason, replica_name)
        
        if not success:
            raise HTTPException(status_code=400, detail="Replica promotion failed")
        
        return {
            "status": "promoted",
            "promoted_replica": replica_name,
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid reason: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/recover/{primary_name}")
async def recover_primary(
    primary_name: str,
    request: RecoverPrimaryRequest,
    failover_mgr: Any = Depends(get_failover_manager)
) -> Dict[str, Any]:
    """Recover old primary as replica."""
    try:
        success = failover_mgr.begin_recovery(primary_name)
        if not success:
            raise HTTPException(status_code=400, detail="Recovery initiation failed")
        
        return {
            "status": "recovery_initiated",
            "primary_name": primary_name,
            "state": failover_mgr.metrics.current_state.value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/readonly/{enable}")
async def set_readonly_mode(
    enable: bool,
    failover_mgr: Any = Depends(get_failover_manager)
) -> Dict[str, Any]:
    """Enable/disable read-only mode on cache failure."""
    try:
        success = failover_mgr.set_readonly_mode(enable)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to set readonly mode")
        
        return {
            "status": "updated",
            "readonly_mode": enable,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
