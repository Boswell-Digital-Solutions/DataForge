"""
API Deployment Management REST API Router

FastAPI router providing HTTP endpoints for:
    - Load balancer management and monitoring
    - API instance registration and health
    - Session management and affinity
    - Connection pool monitoring
    - Graceful deployment and drain
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.utils.load_balancer import (
    get_load_balancer,
    LoadBalancingStrategy,
    InstanceStatus,
)
from app.utils.session_manager import (
    get_session_manager,
)


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class APIInstanceRegisterRequest(BaseModel):
    """Request to register API instance."""
    name: str = Field(..., description="Unique instance name")
    host: str = Field(..., description="Instance host address")
    port: int = Field(8000, description="Instance port")
    weight: int = Field(100, description="Load balancer weight (0-1000)")
    max_connections: int = Field(1000, description="Max concurrent connections")


class InstanceStatusResponse(BaseModel):
    """Response with instance status."""
    name: str
    host: str
    port: int
    weight: int
    status: str
    active_connections: int
    max_connections: int
    total_requests: int
    average_response_time_ms: float
    error_rate: float


class LoadBalancerMetricsResponse(BaseModel):
    """Response with load balancer metrics."""
    strategy: str
    total_instances: int
    healthy_instances: int
    unhealthy_instances: int
    total_active_connections: int
    total_requests: int
    error_rate: float


class SelectInstanceRequest(BaseModel):
    """Request to select instance for routing."""
    client_ip: Optional[str] = Field(None, description="Client IP for IP hash")


class DrainInstanceRequest(BaseModel):
    """Request to start draining instance."""
    instance_name: str = Field(..., description="Instance to drain")


class RecoverInstanceRequest(BaseModel):
    """Request to recover drained instance."""
    instance_name: str = Field(..., description="Instance to recover")


class ChangeStrategyRequest(BaseModel):
    """Request to change load balancing strategy."""
    strategy: str = Field(..., description="New strategy")


class SessionCreateRequest(BaseModel):
    """Request to create session."""
    user_id: Optional[str] = Field(None, description="Associated user ID")
    instance_name: str = Field("", description="Target instance for affinity")
    ttl_seconds: Optional[int] = Field(None, description="Custom TTL")


class SessionUpdateRequest(BaseModel):
    """Request to update session data."""
    key: str = Field(..., description="Data key")
    value: Any = Field(..., description="Data value")


class SessionAffinityRequest(BaseModel):
    """Request to set session affinity."""
    session_id: str = Field(..., description="Session ID")
    instance_name: str = Field(..., description="Target instance")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_lb() -> Any:
    """Dependency: get load balancer."""
    return get_load_balancer()


def get_sm() -> Any:
    """Dependency: get session manager."""
    return get_session_manager()


# ============================================================================
# Router Definition
# ============================================================================

router = APIRouter(prefix="/api-deployment", tags=["api-deployment"])


# ============================================================================
# Instance Management Endpoints
# ============================================================================

@router.post("/instances")
async def register_instance(
    request: APIInstanceRegisterRequest,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Register new API instance."""
    try:
        from app.utils.load_balancer import APIInstance
        
        config = APIInstance(
            name=request.name,
            host=request.host,
            port=request.port,
            weight=request.weight,
            max_connections=request.max_connections,
        )
        
        success = lb.register_instance(config)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to register instance")
        
        return {
            "status": "registered",
            "instance_name": request.name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances", response_model=Dict[str, List[InstanceStatusResponse]])
async def list_instances(
    lb: Any = Depends(get_lb)
) -> Dict[str, List[Dict[str, Any]]]:
    """List all registered instances."""
    try:
        statuses = lb.get_all_instances_status()
        return statuses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/{instance_name}", response_model=InstanceStatusResponse)
async def get_instance_status(
    instance_name: str,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Get status of specific instance."""
    try:
        status = lb.get_instance_status(instance_name)
        if not status:
            raise HTTPException(status_code=404, detail="Instance not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/instances/{instance_name}")
async def unregister_instance(
    instance_name: str,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Unregister instance."""
    try:
        success = lb.unregister_instance(instance_name)
        if not success:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        return {
            "status": "unregistered",
            "instance_name": instance_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Load Balancer Endpoints
# ============================================================================

@router.get("/metrics", response_model=LoadBalancerMetricsResponse)
async def get_lb_metrics(
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Get load balancer metrics."""
    try:
        return lb.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy")
async def get_strategy(
    lb: Any = Depends(get_lb)
) -> Dict[str, str]:
    """Get current load balancing strategy."""
    return {"strategy": lb.strategy.value}


@router.post("/strategy")
async def change_strategy(
    request: ChangeStrategyRequest,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Change load balancing strategy."""
    try:
        strategy = LoadBalancingStrategy(request.strategy)
        lb.strategy = strategy
        return {
            "status": "updated",
            "strategy": strategy.value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {request.strategy}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select-instance")
async def select_instance(
    request: SelectInstanceRequest,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Select instance for routing."""
    try:
        selected = lb.select_instance(request.client_ip)
        if not selected:
            raise HTTPException(status_code=503, detail="No healthy instances available")
        
        return {
            "selected_instance": selected,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Deployment Control Endpoints
# ============================================================================

@router.post("/drain/{instance_name}")
async def drain_instance(
    instance_name: str,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Start graceful drain of instance."""
    try:
        success = lb.start_draining(instance_name)
        if not success:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        return {
            "status": "draining",
            "instance_name": instance_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recover/{instance_name}")
async def recover_instance(
    instance_name: str,
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Stop draining and recover instance."""
    try:
        success = lb.stop_draining(instance_name)
        if not success:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        return {
            "status": "recovered",
            "instance_name": instance_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-request/{instance_name}")
async def record_request(
    instance_name: str,
    response_time_ms: float = Query(...),
    success: bool = Query(True),
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Record request metrics for instance."""
    try:
        lb.record_request(instance_name, response_time_ms, success)
        return {
            "status": "recorded",
            "instance_name": instance_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health-check/{instance_name}")
async def report_health_check(
    instance_name: str,
    is_healthy: bool = Query(...),
    lb: Any = Depends(get_lb)
) -> Dict[str, Any]:
    """Report health check result for instance."""
    try:
        lb.check_instance_health(instance_name, is_healthy)
        status = lb.get_instance_status(instance_name)
        
        return {
            "instance_name": instance_name,
            "reported_healthy": is_healthy,
            "current_status": status["status"] if status else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/sessions")
async def create_session(
    request: SessionCreateRequest,
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """Create new session."""
    try:
        session = sm.create_session(
            user_id=request.user_id,
            instance_name=request.instance_name,
            ttl_seconds=request.ttl_seconds,
        )
        
        return {
            "status": "created",
            "session_id": session.session_id,
            "user_id": session.user_id,
            "instance_name": session.instance_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """Get session details."""
    try:
        session = sm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return session.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """Update session data."""
    try:
        success = sm.update_session_data(session_id, request.key, request.value)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return {
            "status": "updated",
            "session_id": session_id,
            "key": request.key,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """Delete session."""
    try:
        success = sm.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "status": "deleted",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/affinity")
async def set_session_affinity(
    session_id: str,
    request: SessionAffinityRequest,
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """Set session instance affinity (sticky routing)."""
    try:
        success = sm.set_instance_affinity(session_id, request.instance_name)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return {
            "status": "updated",
            "session_id": session_id,
            "instance_name": request.instance_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """List all active sessions."""
    try:
        sessions = sm.get_all_sessions()
        counts = sm.get_session_count()
        
        return {
            "sessions": sessions,
            "counts": counts,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connection-pools")
async def get_pool_metrics(
    sm: Any = Depends(get_sm)
) -> Dict[str, Any]:
    """Get connection pool metrics."""
    try:
        pools = sm.get_pool_metrics()
        return {
            "pools": pools,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
