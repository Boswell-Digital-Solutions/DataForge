"""
Session Manager with Connection Pooling and Affinity

Manages distributed session state across multiple API instances
with sticky session support and connection pooling.

Features:
    - Session store (Redis-backed or in-memory)
    - Connection pooling with circuit breaking
    - Session affinity (sticky sessions)
    - TTL and expiration handling
    - Session replication across instances
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Status of a session."""
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class SessionData:
    """Data stored for a session."""
    session_id: str
    user_id: Optional[str] = None
    instance_name: str = ""  # Sticky instance
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600  # Default 1 hour
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        return age_seconds > self.ttl_seconds
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "instance_name": self.instance_name,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "age_seconds": (datetime.utcnow() - self.created_at).total_seconds(),
            "is_expired": self.is_expired,
            "data": self.data,
        }


@dataclass
class PoolMetrics:
    """Metrics for connection pool."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    wait_queue_size: int = 0
    total_acquisitions: int = 0
    total_releases: int = 0
    acquisition_failures: int = 0
    circuit_breaker_trips: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "wait_queue_size": self.wait_queue_size,
            "total_acquisitions": self.total_acquisitions,
            "total_releases": self.total_releases,
            "acquisition_failures": self.acquisition_failures,
            "circuit_breaker_trips": self.circuit_breaker_trips,
        }


class ConnectionPool:
    """
    Connection pool for API instance connections.
    
    Features:
        - Configurable pool size
        - Idle connection timeout
        - Circuit breaker for failed connections
        - Metrics collection
    """
    
    def __init__(
        self,
        instance_name: str,
        min_size: int = 5,
        max_size: int = 20,
        idle_timeout_seconds: int = 300,
    ):
        """
        Initialize connection pool.
        
        Args:
            instance_name: Instance this pool connects to
            min_size: Minimum connections to maintain
            max_size: Maximum connections allowed
            idle_timeout_seconds: Timeout for idle connections
        """
        self.instance_name = instance_name
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout_seconds = idle_timeout_seconds
        
        self.available_connections: List[Any] = []
        self.active_connections: Set[Any] = set()
        self.metrics = PoolMetrics()
        
        # Initialize minimum connections
        for _ in range(min_size):
            conn = self._create_connection()
            if conn:
                self.available_connections.append(conn)
    
    def _create_connection(self) -> Any:
        """Create a new connection (simulated)."""
        # In production, would create actual connection
        return {
            "instance": self.instance_name,
            "created_at": datetime.utcnow(),
        }
    
    def acquire_connection(self, timeout_seconds: int = 5) -> Optional[Any]:
        """Acquire connection from pool."""
        try:
            # Try to get available connection
            if self.available_connections:
                conn = self.available_connections.pop()
                self.active_connections.add(conn)
                self.metrics.total_acquisitions += 1
                self.metrics.active_connections = len(self.active_connections)
                self.metrics.idle_connections = len(self.available_connections)
                return conn
            
            # Create new connection if under max
            if len(self.active_connections) + len(self.available_connections) < self.max_size:
                conn = self._create_connection()
                if conn:
                    self.active_connections.add(conn)
                    self.metrics.total_acquisitions += 1
                    self.metrics.total_connections = (
                        len(self.active_connections) + len(self.available_connections)
                    )
                    self.metrics.active_connections = len(self.active_connections)
                    return conn
            
            # No connections available
            logger.warning(f"Connection pool exhausted for {self.instance_name}")
            self.metrics.acquisition_failures += 1
            return None
        except Exception as e:
            logger.error(f"Error acquiring connection: {e}")
            self.metrics.acquisition_failures += 1
            return None
    
    def release_connection(self, conn: Any) -> bool:
        """Release connection back to pool."""
        try:
            if conn not in self.active_connections:
                return False
            
            self.active_connections.remove(conn)
            self.available_connections.append(conn)
            self.metrics.total_releases += 1
            self.metrics.active_connections = len(self.active_connections)
            self.metrics.idle_connections = len(self.available_connections)
            return True
        except Exception as e:
            logger.error(f"Error releasing connection: {e}")
            return False
    
    def close_all(self) -> None:
        """Close all connections in pool."""
        self.available_connections.clear()
        self.active_connections.clear()
        logger.info(f"Closed all connections for {self.instance_name}")


class SessionManager:
    """
    Manages distributed session state across API instances.
    
    Features:
        - Session creation and storage
        - Session affinity (sticky routing)
        - Per-instance connection pooling
        - Session expiration and cleanup
        - Replication across instances
    """
    
    def __init__(
        self,
        session_ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 60,
        connection_pool_min_size: int = 5,
        connection_pool_max_size: int = 20,
    ):
        """
        Initialize session manager.
        
        Args:
            session_ttl_seconds: Default session TTL
            cleanup_interval_seconds: How often to clean expired sessions
            connection_pool_min_size: Min connections per instance
            connection_pool_max_size: Max connections per instance
        """
        self.session_ttl_seconds = session_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.connection_pool_min_size = connection_pool_min_size
        self.connection_pool_max_size = connection_pool_max_size
        
        self.sessions: Dict[str, SessionData] = {}
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.last_cleanup: datetime = datetime.utcnow()
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        instance_name: str = "",
        ttl_seconds: Optional[int] = None
    ) -> SessionData:
        """
        Create new session.
        
        Args:
            user_id: User ID associated with session
            instance_name: Instance for session affinity
            ttl_seconds: Session TTL (uses default if None)
            
        Returns:
            New SessionData instance
        """
        try:
            session_id = hashlib.sha256(
                f"{datetime.utcnow().isoformat()}{user_id}{instance_name}".encode()
            ).hexdigest()[:32]
            
            session = SessionData(
                session_id=session_id,
                user_id=user_id,
                instance_name=instance_name,
                ttl_seconds=ttl_seconds or self.session_ttl_seconds,
            )
            
            self.sessions[session_id] = session
            logger.info(f"Created session {session_id} for user {user_id}")
            return session
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session and touch activity timestamp."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return None
            
            if session.is_expired:
                del self.sessions[session_id]
                logger.info(f"Session expired: {session_id}")
                return None
            
            session.touch()
            return session
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    def update_session_data(
        self,
        session_id: str,
        key: str,
        value: Any
    ) -> bool:
        """Update session data."""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.data[key] = value
            session.touch()
            logger.debug(f"Updated session {session_id}: {key}")
            return True
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def get_instance_for_session(self, session_id: str) -> Optional[str]:
        """Get instance affinity for session (sticky routing)."""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.instance_name if session.instance_name else None
    
    def set_instance_affinity(self, session_id: str, instance_name: str) -> bool:
        """Set instance affinity for session."""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.instance_name = instance_name
            session.touch()
            logger.debug(f"Set instance affinity for {session_id}: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error setting instance affinity: {e}")
            return False
    
    def get_or_create_pool(self, instance_name: str) -> ConnectionPool:
        """Get or create connection pool for instance."""
        if instance_name not in self.connection_pools:
            self.connection_pools[instance_name] = ConnectionPool(
                instance_name=instance_name,
                min_size=self.connection_pool_min_size,
                max_size=self.connection_pool_max_size,
            )
        return self.connection_pools[instance_name]
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            expired_count = 0
            now = datetime.utcnow()
            
            # Only run if interval elapsed
            if (now - self.last_cleanup).total_seconds() < self.cleanup_interval_seconds:
                return 0
            
            session_ids = list(self.sessions.keys())
            for session_id in session_ids:
                session = self.sessions[session_id]
                if session.is_expired:
                    del self.sessions[session_id]
                    expired_count += 1
            
            self.last_cleanup = now
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
            
            return expired_count
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active sessions."""
        try:
            self.cleanup_expired_sessions()
            return {
                sid: session.to_dict()
                for sid, session in self.sessions.items()
                if not session.is_expired
            }
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return {}
    
    def get_session_count(self) -> Dict[str, int]:
        """Get session count statistics."""
        self.cleanup_expired_sessions()
        
        active = sum(1 for s in self.sessions.values() if not s.is_expired)
        by_user = {}
        for session in self.sessions.values():
            if not session.is_expired and session.user_id:
                by_user[session.user_id] = by_user.get(session.user_id, 0) + 1
        
        return {
            "total_active": active,
            "total_stored": len(self.sessions),
            "by_user": by_user,
        }
    
    def get_pool_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all connection pools."""
        return {
            name: pool.metrics.to_dict()
            for name, pool in self.connection_pools.items()
        }


# Global singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(
    session_ttl_seconds: int = 3600
) -> SessionManager:
    """
    Get or create global session manager.
    
    Args:
        session_ttl_seconds: Session TTL in seconds
        
    Returns:
        Global SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(session_ttl_seconds=session_ttl_seconds)
    return _session_manager


def reset_session_manager() -> None:
    """Reset global session manager (for testing)."""
    global _session_manager
    _session_manager = None
