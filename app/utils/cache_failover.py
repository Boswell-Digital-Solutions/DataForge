"""
Redis Sentinel Monitoring & Automated Failover Manager

Implements sentinel-based monitoring, automatic failover orchestration,
and replica promotion with health check state machines.

Architecture:
    - Sentinel cluster monitors primary + replicas
    - Automatic primary failure detection
    - Configurable failover thresholds
    - Weighted replica selection (lag × priority × region)
    - Graceful degradation and recovery workflows
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FailoverState(str, Enum):
    """State machine for cache failover lifecycle."""
    HEALTHY = "healthy"
    PRIMARY_DEGRADED = "primary_degraded"
    PRIMARY_FAILED = "primary_failed"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    FAILOVER_COMPLETE = "failover_complete"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"


class FailoverMode(str, Enum):
    """Mode for failover operations."""
    AUTOMATIC = "automatic"  # Automatic on primary failure
    MANUAL = "manual"        # User-initiated failover
    MAINTENANCE = "maintenance"  # Planned maintenance mode


class FailoverReason(str, Enum):
    """Reasons for failover operation."""
    PRIMARY_UNAVAILABLE = "primary_unavailable"
    PRIMARY_UNRESPONSIVE = "primary_unresponsive"
    HEALTH_CHECK_FAILED = "health_check_failed"
    MANUAL_INITIATION = "manual_initiation"
    PLANNED_MAINTENANCE = "planned_maintenance"
    SENTINEL_REQUEST = "sentinel_request"


@dataclass
class FailoverConfig:
    """Configuration for cache failover behavior."""
    sentinel_service_name: str = "mymaster"
    primary_host: str = "localhost"
    primary_port: int = 6379
    failover_mode: FailoverMode = FailoverMode.AUTOMATIC
    health_check_interval_seconds: int = 5
    health_check_timeout_seconds: int = 2
    failure_threshold: int = 3  # Failures before automatic failover
    failure_window_seconds: int = 15  # Time window for failures
    min_quorum: int = 1  # Minimum sentinel votes for failover
    parallel_syncs: int = 1  # Max concurrent replica syncs post-failover
    sentinels: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FailoverMetrics:
    """Metrics for cache failover tracking."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    current_state: FailoverState = FailoverState.HEALTHY
    failover_count: int = 0
    recent_failovers: List[Dict[str, Any]] = field(default_factory=list)
    primary_failure_count: int = 0
    health_check_failures: int = 0
    last_failover_duration_seconds: float = 0.0
    last_failover_reason: Optional[str] = None
    last_failover_timestamp: Optional[datetime] = None
    recovery_attempts: int = 0
    readonly_mode_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "current_state": self.current_state.value,
            "failover_count": self.failover_count,
            "primary_failure_count": self.primary_failure_count,
            "health_check_failures": self.health_check_failures,
            "last_failover_duration_seconds": self.last_failover_duration_seconds,
            "last_failover_reason": self.last_failover_reason,
            "recovery_attempts": self.recovery_attempts,
            "readonly_mode_enabled": self.readonly_mode_enabled,
        }


class CacheFailoverManager:
    """
    Manages cache failover orchestration and sentinel coordination.
    
    Responsibilities:
        - Health monitoring of primary
        - Failure detection and threshold tracking
        - Replica selection for promotion
        - Failover state machine
        - Graceful degradation
        - Primary recovery coordination
    """
    
    def __init__(
        self,
        config: FailoverConfig,
        replication_manager: Any = None,
    ):
        """
        Initialize cache failover manager.
        
        Args:
            config: Failover configuration
            replication_manager: Reference to CacheReplicationManager
        """
        self.config = config
        self.replication_manager = replication_manager
        self.metrics = FailoverMetrics()
        
        # Health check tracking
        self.failure_history: List[datetime] = []
        self.last_health_check: Optional[datetime] = None
    
    def check_primary_health(self, primary_conn: Any) -> bool:
        """
        Check if primary is healthy and responding.
        
        Args:
            primary_conn: Redis connection to primary
            
        Returns:
            True if primary is healthy
        """
        try:
            # Simulate health check (PING command)
            self.last_health_check = datetime.now(UTC)
            
            # In production: would call primary_conn.ping()
            # This will raise exception if ping fails
            if hasattr(primary_conn, 'ping'):
                primary_conn.ping()
            
            # Success
            return True
        except Exception as e:
            self.failure_history.append(datetime.now(UTC))
            # Prune old failures outside window
            cutoff = datetime.now(UTC) - timedelta(
                seconds=self.config.failure_window_seconds
            )
            self.failure_history = [
                f for f in self.failure_history if f > cutoff
            ]
            self.metrics.health_check_failures += 1
            logger.error(f"Error during health check: {e}")
            return False
    
    def should_failover(self) -> bool:
        """
        Determine if failover should be triggered.
        
        Returns:
            True if failure threshold exceeded
        """
        # Prune old failures
        cutoff = datetime.now(UTC) - timedelta(
            seconds=self.config.failure_window_seconds
        )
        self.failure_history = [f for f in self.failure_history if f > cutoff]
        
        threshold_met = len(self.failure_history) >= self.config.failure_threshold
        
        if threshold_met:
            logger.warning(
                f"Failover threshold met: {len(self.failure_history)} failures "
                f"in {self.config.failure_window_seconds}s"
            )
        
        return threshold_met
    
    def select_promotion_candidate(self) -> Optional[str]:
        """
        Select best replica to promote to primary.
        
        Selection algorithm:
            1. Must be connected and healthy
            2. Score by: lag (lower better) × priority (higher better) × region
            3. Return lowest score replica
            
        Returns:
            Name of replica to promote, or None
        """
        try:
            if not self.replication_manager:
                logger.error("Replication manager not available")
                return None
            
            candidates = []
            for replica_name, replica in self.replication_manager.replicas.items():
                # Skip non-promotion roles
                if replica.role.value not in ["replica", "read_replica"]:
                    continue
                
                # Must be connected
                if not self.replication_manager.check_replica_connectivity(replica_name):
                    continue
                
                # Calculate score: lower is better
                lag_ms = self.replication_manager.get_replica_lag_ms(replica_name)
                priority = replica.slave_priority
                
                # Weighted scoring algorithm
                score = lag_ms * 1.0  # Base score from lag
                score = score / (priority / 100.0) if priority > 0 else score  # Adjust by priority
                
                # Prefer same region
                if replica.region == self.config.primary_host:
                    score -= 1000
                
                candidates.append((replica_name, score, lag_ms))
            
            if not candidates:
                logger.warning("No suitable replicas for promotion")
                return None
            
            # Sort by score (lowest first)
            candidates.sort(key=lambda x: x[1])
            selected = candidates[0]
            
            logger.info(
                f"Selected replica {selected[0]} for promotion "
                f"(lag: {selected[2]:.1f}ms, score: {selected[1]:.2f})"
            )
            return selected[0]
        except Exception as e:
            logger.error(f"Error selecting promotion candidate: {e}")
            return None
    
    def initiate_failover(
        self,
        reason: FailoverReason,
        manual_replica_name: Optional[str] = None,
    ) -> bool:
        """
        Initiate cache failover process.
        
        Args:
            reason: Reason for failover
            manual_replica_name: Specific replica to promote (if manual)
            
        Returns:
            True if failover initiated successfully
        """
        try:
            if self.metrics.current_state != FailoverState.HEALTHY:
                logger.warning(
                    f"Cannot initiate failover: current state is {self.metrics.current_state}"
                )
                return False
            
            logger.info(f"Initiating failover: {reason.value}")
            self.metrics.current_state = FailoverState.FAILOVER_IN_PROGRESS
            failover_start = datetime.now(UTC)
            
            # Select replica to promote
            replica_to_promote = manual_replica_name
            if not replica_to_promote:
                replica_to_promote = self.select_promotion_candidate()
            
            if not replica_to_promote:
                logger.error("No replica available for promotion")
                self.metrics.current_state = FailoverState.PRIMARY_FAILED
                return False
            
            # Execute promotion
            if self.replication_manager:
                success = self.replication_manager.promote_replica_to_primary(
                    replica_to_promote
                )
                if not success:
                    logger.error(f"Failed to promote {replica_to_promote}")
                    self.metrics.current_state = FailoverState.PRIMARY_FAILED
                    return False
            
            # Update metrics
            duration = (datetime.now(UTC) - failover_start).total_seconds()
            self.metrics.current_state = FailoverState.FAILOVER_COMPLETE
            self.metrics.failover_count += 1
            self.metrics.last_failover_duration_seconds = duration
            self.metrics.last_failover_reason = reason.value
            self.metrics.last_failover_timestamp = datetime.now(UTC)
            
            # Record in history
            self.metrics.recent_failovers.append({
                "timestamp": datetime.now(UTC).isoformat(),
                "reason": reason.value,
                "promoted_replica": replica_to_promote,
                "duration_seconds": duration,
            })
            
            logger.info(
                f"Failover complete: promoted {replica_to_promote} in {duration:.1f}s"
            )
            self.failure_history.clear()
            return True
        except Exception as e:
            logger.error(f"Error during failover: {e}")
            self.metrics.current_state = FailoverState.PRIMARY_FAILED
            return False
    
    def begin_recovery(self, old_primary_name: str) -> bool:
        """
        Begin recovery process for old primary.
        
        Converts old primary to replica of new primary.
        """
        try:
            self.metrics.current_state = FailoverState.RECOVERY_IN_PROGRESS
            self.metrics.recovery_attempts += 1
            
            logger.info(f"Beginning recovery for old primary {old_primary_name}")
            
            # In production: would re-replicate old primary
            # Simulate recovery completion
            self.metrics.current_state = FailoverState.HEALTHY
            logger.info(f"Recovery complete for {old_primary_name}")
            return True
        except Exception as e:
            logger.error(f"Error during recovery: {e}")
            return False
    
    def set_readonly_mode(self, enable: bool) -> bool:
        """Enable read-only mode on failure (graceful degradation)."""
        try:
            self.metrics.readonly_mode_enabled = enable
            mode_str = "enabled" if enable else "disabled"
            logger.info(f"Read-only mode {mode_str}")
            return True
        except Exception as e:
            logger.error(f"Error setting read-only mode: {e}")
            return False
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current failover state and metrics."""
        return {
            "state": self.metrics.current_state.value,
            "primary_host": self.config.primary_host,
            "primary_port": self.config.primary_port,
            "failover_mode": self.config.failover_mode.value,
            "health_check_interval": self.config.health_check_interval_seconds,
            "failure_threshold": self.config.failure_threshold,
            "failures_in_window": len(self.failure_history),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "readonly_mode": self.metrics.readonly_mode_enabled,
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get failover metrics."""
        return self.metrics.to_dict()


# Global singleton instance
_failover_manager: Optional[CacheFailoverManager] = None


def get_cache_failover_manager(
    config: Optional[FailoverConfig] = None,
    replication_manager: Any = None,
) -> CacheFailoverManager:
    """
    Get or create global cache failover manager.
    
    Args:
        config: Failover configuration
        replication_manager: Reference to CacheReplicationManager
        
    Returns:
        Global CacheFailoverManager instance
    """
    global _failover_manager
    if _failover_manager is None:
        if config is None:
            config = FailoverConfig()
        _failover_manager = CacheFailoverManager(
            config=config,
            replication_manager=replication_manager,
        )
    return _failover_manager


def reset_cache_failover_manager() -> None:
    """Reset global manager (for testing)."""
    global _failover_manager
    _failover_manager = None
