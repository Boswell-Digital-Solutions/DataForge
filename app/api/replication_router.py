"""REST API routes for database replication and failover management."""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/replication",
    tags=["replication"],
    responses={500: {"description": "Internal server error"}},
)


# Pydantic Models for request/response

class ReplicaRegisterRequest(BaseModel):
    """Request to register a new replica."""
    replica_name: str = Field(..., description="Unique replica identifier")
    primary_host: str = Field(..., description="Primary database host")
    replica_host: str = Field(..., description="Replica database host")
    replica_port: int = Field(5432, description="Replica database port")
    role: str = Field("standby", description="Replica role (standby, cascading, read_replica)")
    region: str = Field(..., description="Geographic region")
    sync_mode: str = Field("asynchronous", description="Replication mode (asynchronous, synchronous, quorum)")


class ReplicaStatusResponse(BaseModel):
    """Response with replica status information."""
    replica_name: str
    status: str
    sync_state: Optional[str] = None
    lag_seconds: Optional[float] = None
    lag_bytes: Optional[int] = None
    is_lagged: bool = False


class ReplicationMetricsResponse(BaseModel):
    """Response with replication metrics."""
    total_replicas: int
    active_replicas: int
    lagged_replicas: int
    sync_replica_count: int
    replication_failures: int
    failover_count: int
    streaming_errors: int


class FailoverRequest(BaseModel):
    """Request to initiate failover."""
    reason: Optional[str] = Field(None, description="Reason for failover")
    auto: bool = Field(True, description="Automatic failover")


class PromoteReplicaRequest(BaseModel):
    """Request to promote a replica to primary."""
    replica_name: str = Field(..., description="Replica to promote")


class SyncModeRequest(BaseModel):
    """Request to set sync mode for a replica."""
    sync: bool = Field(..., description="True for synchronous, False for asynchronous")


# Dependency to get replication manager
def get_replication_manager() -> Any:
    """Get replication manager instance."""
    from app.utils.db_replication import get_replication_manager as get_mgr
    try:
        # Would use actual database connection in production
        return get_mgr(None)
    except Exception as e:
        logger.error(f"Failed to get replication manager: {e}")
        raise HTTPException(status_code=500, detail="Replication manager unavailable")


def get_failover_manager() -> Any:
    """Get failover manager instance."""
    from app.utils.db_failover import get_failover_manager as get_mgr
    try:
        rep_mgr = get_replication_manager()
        return get_mgr(rep_mgr)
    except Exception as e:
        logger.error(f"Failed to get failover manager: {e}")
        raise HTTPException(status_code=500, detail="Failover manager unavailable")


# Health & Status Endpoints

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Check replication subsystem health."""
    try:
        rep_mgr = get_replication_manager()
        metrics = rep_mgr.get_metrics()
        
        return {
            "status": "healthy",
            "replicas_active": metrics.active_replicas,
            "replicas_total": metrics.total_replicas,
            "errors": metrics.streaming_errors,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Replication health check failed")


@router.get("/metrics", response_model=ReplicationMetricsResponse)
async def get_metrics():
    """Get aggregated replication metrics."""
    try:
        rep_mgr = get_replication_manager()
        metrics = rep_mgr.get_metrics()
        
        return ReplicationMetricsResponse(
            total_replicas=metrics.total_replicas,
            active_replicas=metrics.active_replicas,
            lagged_replicas=metrics.lagged_replicas,
            sync_replica_count=metrics.sync_replica_count,
            replication_failures=metrics.replication_failures,
            failover_count=metrics.failover_count,
            streaming_errors=metrics.streaming_errors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Replica Management Endpoints

@router.get("/replicas", response_model=Dict[str, Any])
async def list_replicas():
    """List all configured replicas."""
    try:
        rep_mgr = get_replication_manager()
        replicas = rep_mgr.get_replica_list()
        
        return {"replicas": replicas, "count": len(replicas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replicas", response_model=Dict[str, Any])
async def register_replica(req: ReplicaRegisterRequest):
    """Register a new replica."""
    try:
        from app.utils.db_replication import ReplicaConfig, ReplicaRole, ReplicationMode
        
        rep_mgr = get_replication_manager()
        
        config = ReplicaConfig(
            replica_name=req.replica_name,
            primary_host=req.primary_host,
            replica_host=req.replica_host,
            replica_port=req.replica_port,
            role=ReplicaRole(req.role),
            region=req.region,
            sync_mode=ReplicationMode(req.sync_mode),
        )
        
        success = rep_mgr.register_replica(config)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to register replica")
        
        return {
            "success": True,
            "replica_name": req.replica_name,
            "message": f"Replica {req.replica_name} registered successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
    except Exception as e:
        logger.error(f"Failed to register replica: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replicas/{replica_name}", response_model=Dict[str, Any])
async def get_replica_status(replica_name: str):
    """Get detailed status of a replica."""
    try:
        rep_mgr = get_replication_manager()
        status = rep_mgr.get_replica_status(replica_name)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Replica {replica_name} not found")
        
        lag = rep_mgr.get_replica_lag(replica_name)
        
        return {
            "replica_name": replica_name,
            "status": status,
            "lag": lag,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replicas/{replica_name}/lag", response_model=Dict[str, Any])
async def get_replica_lag(replica_name: str):
    """Get replication lag for a replica."""
    try:
        rep_mgr = get_replication_manager()
        lag = rep_mgr.get_replica_lag(replica_name)
        
        if not lag:
            raise HTTPException(status_code=404, detail=f"Could not get lag for {replica_name}")
        
        return lag
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/replicas/{replica_name}", response_model=Dict[str, Any])
async def unregister_replica(replica_name: str):
    """Unregister a replica."""
    try:
        rep_mgr = get_replication_manager()
        success = rep_mgr.unregister_replica(replica_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Replica {replica_name} not found")
        
        return {
            "success": True,
            "replica_name": replica_name,
            "message": f"Replica {replica_name} unregistered",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replicas/{replica_name}/sync-mode", response_model=Dict[str, Any])
async def set_sync_mode(replica_name: str, req: SyncModeRequest):
    """Set synchronous or asynchronous mode for a replica."""
    try:
        rep_mgr = get_replication_manager()
        success = rep_mgr.set_synchronous_mode(replica_name, req.sync)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Replica {replica_name} not found")
        
        mode = "synchronous" if req.sync else "asynchronous"
        return {
            "success": True,
            "replica_name": replica_name,
            "sync_mode": mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WAL & Replication Slot Endpoints

@router.get("/wal-position", response_model=Dict[str, Any])
async def get_wal_position():
    """Get current WAL position on primary."""
    try:
        rep_mgr = get_replication_manager()
        wal_pos = rep_mgr.get_wal_position()
        
        if not wal_pos:
            raise HTTPException(status_code=500, detail="Could not retrieve WAL position")
        
        return wal_pos
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replication-slots", response_model=Dict[str, Any])
async def get_replication_slots():
    """Get active replication slots."""
    try:
        rep_mgr = get_replication_manager()
        slots = rep_mgr.get_replication_slots()
        
        if slots is None:
            raise HTTPException(status_code=500, detail="Could not retrieve replication slots")
        
        return {"slots": slots, "count": len(slots)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Failover Endpoints

@router.get("/failover/state", response_model=Dict[str, Any])
async def get_failover_state():
    """Get current failover state."""
    try:
        failover_mgr = get_failover_manager()
        state = failover_mgr.get_current_state()
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/initiate", response_model=Dict[str, Any])
async def initiate_failover(req: FailoverRequest):
    """Initiate failover to a replica."""
    try:
        failover_mgr = get_failover_manager()
        reason = req.reason or "Manual failover initiated"
        
        success = failover_mgr.initiate_failover(reason)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failover failed")
        
        return {
            "success": True,
            "message": "Failover completed successfully",
            "promoted_replica": failover_mgr._promoted_replica,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failover failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/promote/{replica_name}", response_model=Dict[str, Any])
async def promote_replica(replica_name: str):
    """Manually promote a replica to primary."""
    try:
        failover_mgr = get_failover_manager()
        success = failover_mgr.promote_replica_manual(replica_name)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to promote {replica_name}")
        
        return {
            "success": True,
            "replica_name": replica_name,
            "message": f"{replica_name} promoted to primary",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Promotion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/failover/recover/{replica_name}", response_model=Dict[str, Any])
async def recover_primary(replica_name: str):
    """Recover old primary as new standby."""
    try:
        failover_mgr = get_failover_manager()
        success = failover_mgr.recover_primary(replica_name)
        
        if not success:
            raise HTTPException(status_code=500, detail="Recovery failed")
        
        return {
            "success": True,
            "message": "Primary recovery completed",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failover/metrics", response_model=Dict[str, Any])
async def get_failover_metrics():
    """Get failover metrics."""
    try:
        failover_mgr = get_failover_manager()
        metrics = failover_mgr.get_metrics()
        
        return {
            "total_failovers": metrics.total_failovers,
            "successful_failovers": metrics.successful_failovers,
            "failed_failovers": metrics.failed_failovers,
            "primary_failures": metrics.primary_failures,
            "primary_recoveries": metrics.primary_recoveries,
            "health_check_failures": metrics.health_check_failures,
            "last_failover_time": metrics.last_failover_time,
            "last_failover_reason": metrics.last_failover_reason,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
