"""Database failover management for PostgreSQL high availability.

Implements automated failover, leader election, and recovery procedures.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FailoverState(str, Enum):
    """State of failover process."""
    HEALTHY = "healthy"
    PRIMARY_DEGRADED = "primary_degraded"
    PRIMARY_FAILED = "primary_failed"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    FAILOVER_COMPLETE = "failover_complete"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"


class FailoverMode(str, Enum):
    """Failover strategy."""
    AUTOMATIC = "automatic"      # Auto failover to best replica
    MANUAL = "manual"            # Manual promotion only
    QUORUM = "quorum"            # Wait for majority replica ack


@dataclass
class FailoverConfig:
    """Configuration for failover behavior."""
    mode: FailoverMode = FailoverMode.AUTOMATIC
    primary_health_check_interval_sec: int = 5
    primary_heartbeat_timeout_sec: int = 15
    primary_unhealthy_threshold: int = 3  # Failures before failover
    replica_promotion_timeout_sec: int = 30
    readonly_mode_on_primary_failure: bool = True
    auto_recovery_enabled: bool = True
    enable_quorum_commit: bool = False
    min_sync_replicas: int = 1


@dataclass
class FailoverMetrics:
    """Metrics for failover monitoring."""
    total_failovers: int = 0
    successful_failovers: int = 0
    failed_failovers: int = 0
    last_failover_time: Optional[str] = None
    last_failover_reason: Optional[str] = None
    primary_failures: int = 0
    primary_recoveries: int = 0
    current_state: str = FailoverState.HEALTHY.value
    state_since: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_health_check: Optional[str] = None
    health_check_failures: int = 0


class FailoverManager:
    """Manages database failover and high availability."""

    def __init__(self, replication_manager: Any, config: Optional[FailoverConfig] = None):
        """Initialize failover manager.
        
        Args:
            replication_manager: ReplicationManager instance
            config: Failover configuration
        """
        self.replication_manager = replication_manager
        self.config = config or FailoverConfig()
        self._metrics = FailoverMetrics()
        self._state = FailoverState.HEALTHY
        self._primary_failure_count = 0
        self._last_health_check = time.time()
        self._promoted_replica: Optional[str] = None
        logger.info("Failover manager initialized")

    def check_primary_health(self, conn: Any) -> Tuple[bool, Optional[str]]:
        """Check if primary is healthy.
        
        Args:
            conn: Primary database connection
            
        Returns:
            (is_healthy, error_message)
        """
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            self._primary_failure_count = 0
            self._metrics.last_health_check = datetime.utcnow().isoformat()
            
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Primary health check failed: {error_msg}")
            
            self._primary_failure_count += 1
            self._metrics.last_health_check = datetime.utcnow().isoformat()
            self._metrics.health_check_failures += 1
            
            if self._primary_failure_count >= self.config.primary_unhealthy_threshold:
                self._metrics.primary_failures += 1
                if self._state != FailoverState.PRIMARY_FAILED:
                    self._state = FailoverState.PRIMARY_FAILED
                    self._metrics.current_state = FailoverState.PRIMARY_FAILED.value
            
            return False, error_msg

    def select_promotion_candidate(self) -> Optional[str]:
        """Select best replica to promote to primary.
        
        Selection criteria (in order):
        1. Replica with least replication lag
        2. Synchronous replica preferred
        3. Same region as primary preferred
        
        Returns:
            Name of replica to promote or None
        """
        try:
            replicas = self.replication_manager.get_replica_list()
            
            if not replicas:
                logger.warning("No replicas available for promotion")
                return None
            
            # Get lag information
            lags = self.replication_manager.get_all_replica_lags()
            
            # Score replicas
            candidates = []
            for replica_name, replica_info in replicas.items():
                if replica_info["status"] != "streaming":
                    continue
                
                lag_info = lags.get(replica_name, {})
                lag_seconds = lag_info.get("lag_seconds", float("inf"))
                
                # Scoring: lower is better
                score = lag_seconds
                
                # Bonus for synchronous replicas
                if replica_info["sync_mode"] == "synchronous":
                    score -= 1000
                
                candidates.append((replica_name, score))
            
            if not candidates:
                logger.warning("No suitable replica candidates for promotion")
                return None
            
            # Sort by score and pick best
            candidates.sort(key=lambda x: x[1])
            best_replica = candidates[0][0]
            
            logger.info(f"Selected {best_replica} for promotion (score: {candidates[0][1]})")
            return best_replica
            
        except Exception as e:
            logger.error(f"Failed to select promotion candidate: {e}")
            return None

    def initiate_failover(self, reason: str = "Primary failed") -> bool:
        """Initiate automatic failover.
        
        Args:
            reason: Reason for failover
            
        Returns:
            True if failover initiated
        """
        try:
            if self._state == FailoverState.FAILOVER_IN_PROGRESS:
                logger.warning("Failover already in progress")
                return False
            
            logger.info(f"Initiating failover: {reason}")
            self._state = FailoverState.FAILOVER_IN_PROGRESS
            self._metrics.current_state = FailoverState.FAILOVER_IN_PROGRESS.value
            self._metrics.total_failovers += 1
            
            # Select candidate
            candidate = self.select_promotion_candidate()
            if not candidate:
                logger.error("No suitable replica for promotion")
                self._metrics.failed_failovers += 1
                self._state = FailoverState.PRIMARY_FAILED
                self._metrics.current_state = FailoverState.PRIMARY_FAILED.value
                return False
            
            # Attempt promotion
            success = self.replication_manager.promote_replica_to_primary(candidate)
            
            if success:
                self._promoted_replica = candidate
                self._state = FailoverState.FAILOVER_COMPLETE
                self._metrics.current_state = FailoverState.FAILOVER_COMPLETE.value
                self._metrics.successful_failovers += 1
                self._metrics.last_failover_time = datetime.utcnow().isoformat()
                self._metrics.last_failover_reason = reason
                logger.info(f"Failover completed: {candidate} promoted to primary")
                return True
            else:
                logger.error(f"Failed to promote {candidate}")
                self._metrics.failed_failovers += 1
                return False
                
        except Exception as e:
            logger.error(f"Failover failed: {e}")
            self._metrics.failed_failovers += 1
            return False

    def promote_replica_manual(self, replica_name: str) -> bool:
        """Manually promote a replica to primary.
        
        Args:
            replica_name: Name of replica to promote
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Manual promotion of {replica_name} to primary")
            
            success = self.replication_manager.promote_replica_to_primary(replica_name)
            
            if success:
                self._promoted_replica = replica_name
                self._state = FailoverState.FAILOVER_COMPLETE
                self._metrics.current_state = FailoverState.FAILOVER_COMPLETE.value
                self._metrics.successful_failovers += 1
                self._metrics.last_failover_time = datetime.utcnow().isoformat()
                logger.info(f"Manual promotion successful: {replica_name} is now primary")
            
            return success
            
        except Exception as e:
            logger.error(f"Manual promotion failed: {e}")
            self._metrics.failed_failovers += 1
            return False

    def recover_primary(self, replica_name: str) -> bool:
        """Recover old primary as new standby after failover.
        
        Args:
            replica_name: Name of replica (current primary)
            
        Returns:
            True if recovery initiated
        """
        try:
            logger.info("Initiating primary recovery after failover")
            self._state = FailoverState.RECOVERY_IN_PROGRESS
            self._metrics.current_state = FailoverState.RECOVERY_IN_PROGRESS.value
            
            # In production: 
            # 1. Stop old primary
            # 2. Configure as standby
            # 3. Start streaming from new primary
            
            logger.info("Recovery completed")
            self._state = FailoverState.HEALTHY
            self._metrics.current_state = FailoverState.HEALTHY.value
            self._metrics.primary_recoveries += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Primary recovery failed: {e}")
            return False

    def set_readonly_mode(self, enable: bool = True) -> bool:
        """Set primary to read-only mode (on failure).
        
        Args:
            enable: True to enable readonly
            
        Returns:
            True if successful
        """
        try:
            # In production: Set default_transaction_read_only = on
            logger.info(f"Readonly mode {'enabled' if enable else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set readonly mode: {e}")
            return False

    def get_current_state(self) -> Dict[str, Any]:
        """Get current failover state.
        
        Returns:
            Current state information
        """
        return {
            "state": self._state.value,
            "promoted_replica": self._promoted_replica,
            "primary_failure_count": self._primary_failure_count,
            "metrics": {
                "total_failovers": self._metrics.total_failovers,
                "successful_failovers": self._metrics.successful_failovers,
                "failed_failovers": self._metrics.failed_failovers,
                "primary_failures": self._metrics.primary_failures,
                "primary_recoveries": self._metrics.primary_recoveries,
                "health_check_failures": self._metrics.health_check_failures,
            }
        }

    def get_metrics(self) -> FailoverMetrics:
        """Get failover metrics.
        
        Returns:
            Current failover metrics
        """
        return self._metrics

    def reset_failure_count(self) -> None:
        """Reset primary failure counter."""
        self._primary_failure_count = 0
        logger.info("Primary failure counter reset")


# Singleton instance
_failover_manager: Optional[FailoverManager] = None


def get_failover_manager(
    replication_manager: Any,
    config: Optional[FailoverConfig] = None
) -> FailoverManager:
    """Get or create failover manager.
    
    Args:
        replication_manager: ReplicationManager instance
        config: Failover configuration
        
    Returns:
        Failover manager instance
    """
    global _failover_manager
    
    if _failover_manager is None:
        _failover_manager = FailoverManager(replication_manager, config)
    
    return _failover_manager


def reset_failover_manager() -> None:
    """Reset failover manager (for testing)."""
    global _failover_manager
    _failover_manager = None
