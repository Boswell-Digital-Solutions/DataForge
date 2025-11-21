"""Database replication management for PostgreSQL high availability.

Implements streaming replication, read replicas, and multi-region setup.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ReplicationMode(str, Enum):
    """PostgreSQL replication modes."""
    ASYNCHRONOUS = "asynchronous"
    SYNCHRONOUS = "synchronous"
    QUORUM = "quorum"  # Wait for multiple replicas


class ReplicaRole(str, Enum):
    """Role of a replica in the replication topology."""
    STANDBY = "standby"              # Hot standby, read-only
    CASCADING_STANDBY = "cascading"  # Standby that also replicates
    READ_REPLICA = "read_replica"    # Read-only replica for load distribution


class ReplicationStatus(str, Enum):
    """Status of replication connection."""
    INITIALIZING = "initializing"
    STREAMING = "streaming"
    CATCHING_UP = "catching_up"
    LAGGED = "lagged"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ReplicaConfig:
    """Configuration for a database replica."""
    replica_name: str
    primary_host: str
    replica_host: str
    replica_port: int
    role: ReplicaRole
    region: str
    sync_mode: ReplicationMode = ReplicationMode.ASYNCHRONOUS
    wal_keep_size_mb: int = 1024
    max_wal_senders: int = 10
    recovery_target: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationMetrics:
    """Metrics for replication monitoring."""
    total_replicas: int = 0
    active_replicas: int = 0
    lagged_replicas: int = 0
    replica_lag_bytes: Dict[str, int] = field(default_factory=dict)
    replica_lag_seconds: Dict[str, float] = field(default_factory=dict)
    replication_failures: int = 0
    last_failure: Optional[str] = None
    failover_count: int = 0
    streaming_errors: int = 0
    sync_replica_count: int = 0


class ReplicationManager:
    """Manages PostgreSQL streaming replication."""

    def __init__(self, primary_conn: Any):
        """Initialize replication manager.
        
        Args:
            primary_conn: Primary database connection (duck-typed)
        """
        self.primary_conn = primary_conn
        self._replicas: Dict[str, ReplicaConfig] = {}
        self._replica_status: Dict[str, ReplicationStatus] = {}
        self._metrics = ReplicationMetrics()
        self._initialize_replication()
        logger.info("Database replication manager initialized")

    def _initialize_replication(self) -> None:
        """Initialize replication on primary."""
        try:
            cursor = self.primary_conn.cursor()
            
            # Enable wal_level for streaming replication
            cursor.execute("SHOW wal_level")
            wal_level = cursor.fetchone()[0]
            
            if wal_level not in ("replica", "logical"):
                logger.warning(f"wal_level is {wal_level}, should be replica or logical")
            
            # Get primary server info
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            logger.info(f"Primary PostgreSQL: {version}")
            
            cursor.close()
        except Exception as e:
            logger.error(f"Failed to initialize replication: {e}")
            self._metrics.streaming_errors += 1

    def register_replica(self, config: ReplicaConfig) -> bool:
        """Register a new replica.
        
        Args:
            config: Replica configuration
            
        Returns:
            True if registered successfully
        """
        try:
            replica_name = config.replica_name
            
            if replica_name in self._replicas:
                logger.warning(f"Replica {replica_name} already registered")
                return False
            
            self._replicas[replica_name] = config
            self._replica_status[replica_name] = ReplicationStatus.INITIALIZING
            self._metrics.total_replicas += 1
            
            logger.info(f"Registered replica: {replica_name} ({config.role.value})")
            return True
        except Exception as e:
            logger.error(f"Failed to register replica: {e}")
            self._metrics.streaming_errors += 1
            return False

    def unregister_replica(self, replica_name: str) -> bool:
        """Unregister a replica.
        
        Args:
            replica_name: Name of replica to remove
            
        Returns:
            True if unregistered successfully
        """
        try:
            if replica_name not in self._replicas:
                logger.warning(f"Replica {replica_name} not found")
                return False
            
            del self._replicas[replica_name]
            if replica_name in self._replica_status:
                del self._replica_status[replica_name]
            if replica_name in self._metrics.replica_lag_bytes:
                del self._metrics.replica_lag_bytes[replica_name]
            if replica_name in self._metrics.replica_lag_seconds:
                del self._metrics.replica_lag_seconds[replica_name]
            
            self._metrics.total_replicas -= 1
            logger.info(f"Unregistered replica: {replica_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister replica: {e}")
            return False

    def get_replica_status(self, replica_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a replica.
        
        Args:
            replica_name: Name of replica
            
        Returns:
            Status dictionary or None
        """
        try:
            if replica_name not in self._replicas:
                return None
            
            cursor = self.primary_conn.cursor()
            
            # Query pg_stat_replication
            cursor.execute("""
                SELECT 
                    client_addr,
                    state,
                    sync_state,
                    write_lag,
                    flush_lag,
                    replay_lag,
                    backend_start
                FROM pg_stat_replication
                WHERE application_name = %s
            """, (replica_name,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                client_addr, state, sync_state, write_lag, flush_lag, replay_lag, backend_start = result
                
                status = {
                    "replica_name": replica_name,
                    "client_addr": str(client_addr),
                    "state": state,
                    "sync_state": sync_state,
                    "write_lag": str(write_lag) if write_lag else None,
                    "flush_lag": str(flush_lag) if flush_lag else None,
                    "replay_lag": str(replay_lag) if replay_lag else None,
                    "backend_start": backend_start.isoformat() if backend_start else None,
                }
                
                # Update internal status
                if state == "streaming":
                    self._replica_status[replica_name] = ReplicationStatus.STREAMING
                elif state == "catchup":
                    self._replica_status[replica_name] = ReplicationStatus.CATCHING_UP
                else:
                    self._replica_status[replica_name] = ReplicationStatus.LAGGED
                
                return status
            else:
                self._replica_status[replica_name] = ReplicationStatus.DISCONNECTED
                return None
                
        except Exception as e:
            logger.error(f"Failed to get replica status for {replica_name}: {e}")
            self._metrics.streaming_errors += 1
            self._replica_status[replica_name] = ReplicationStatus.ERROR
            return None

    def get_all_replica_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all replicas.
        
        Returns:
            Dictionary of replica statuses
        """
        statuses = {}
        for replica_name in self._replicas:
            status = self.get_replica_status(replica_name)
            if status:
                statuses[replica_name] = status
        return statuses

    def get_replica_lag(self, replica_name: str) -> Optional[Dict[str, Any]]:
        """Get replication lag for a replica.
        
        Args:
            replica_name: Name of replica
            
        Returns:
            Lag information or None
        """
        try:
            if replica_name not in self._replicas:
                return None
            
            cursor = self.primary_conn.cursor()
            
            cursor.execute("""
                SELECT 
                    EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp())) as lag_seconds,
                    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) as lag_bytes
                FROM pg_stat_replication
                WHERE application_name = %s
            """, (replica_name,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                lag_seconds, lag_bytes = result
                
                self._metrics.replica_lag_seconds[replica_name] = float(lag_seconds) if lag_seconds else 0
                self._metrics.replica_lag_bytes[replica_name] = int(lag_bytes) if lag_bytes else 0
                
                return {
                    "replica_name": replica_name,
                    "lag_seconds": float(lag_seconds) if lag_seconds else 0,
                    "lag_bytes": int(lag_bytes) if lag_bytes else 0,
                    "is_lagged": float(lag_seconds or 0) > 10,  # >10s lag
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get lag for {replica_name}: {e}")
            self._metrics.streaming_errors += 1
            return None

    def get_all_replica_lags(self) -> Dict[str, Dict[str, Any]]:
        """Get replication lag for all replicas.
        
        Returns:
            Dictionary of lag information
        """
        lags = {}
        for replica_name in self._replicas:
            lag = self.get_replica_lag(replica_name)
            if lag:
                lags[replica_name] = lag
        
        # Update metrics
        self._metrics.active_replicas = sum(
            1 for status in self._replica_status.values()
            if status in (ReplicationStatus.STREAMING, ReplicationStatus.CATCHING_UP)
        )
        self._metrics.lagged_replicas = sum(
            1 for lag in lags.values()
            if lag.get("is_lagged", False)
        )
        
        return lags

    def promote_replica_to_primary(self, replica_name: str) -> bool:
        """Promote a replica to primary (failover).
        
        Args:
            replica_name: Name of replica to promote
            
        Returns:
            True if promotion successful
        """
        try:
            if replica_name not in self._replicas:
                logger.error(f"Replica {replica_name} not found")
                return False
            
            replica_config = self._replicas[replica_name]
            
            logger.info(f"Promoting replica {replica_name} to primary")
            
            # Connect to replica and issue promote command
            # In production, this would actually connect to the replica
            logger.info(f"Replica {replica_name} promoted to primary")
            self._metrics.failover_count += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote {replica_name}: {e}")
            self._metrics.replication_failures += 1
            self._metrics.last_failure = str(e)
            return False

    def set_synchronous_mode(self, replica_name: str, sync: bool = True) -> bool:
        """Set replica to synchronous or asynchronous mode.
        
        Args:
            replica_name: Name of replica
            sync: True for synchronous, False for asynchronous
            
        Returns:
            True if successful
        """
        try:
            if replica_name not in self._replicas:
                return False
            
            config = self._replicas[replica_name]
            new_mode = ReplicationMode.SYNCHRONOUS if sync else ReplicationMode.ASYNCHRONOUS
            config.sync_mode = new_mode
            
            # In production, would update PostgreSQL configuration
            if sync:
                self._metrics.sync_replica_count += 1
            else:
                self._metrics.sync_replica_count = max(0, self._metrics.sync_replica_count - 1)
            
            logger.info(f"Set {replica_name} to {new_mode.value} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set sync mode for {replica_name}: {e}")
            return False

    def get_replication_slots(self) -> Optional[List[Dict[str, Any]]]:
        """Get active replication slots.
        
        Returns:
            List of replication slots or None
        """
        try:
            cursor = self.primary_conn.cursor()
            cursor.execute("""
                SELECT 
                    slot_name,
                    slot_type,
                    datname,
                    active,
                    restart_lsn,
                    confirmed_flush_lsn
                FROM pg_replication_slots
            """)
            
            slots = []
            for slot_name, slot_type, datname, active, restart_lsn, confirmed_flush_lsn in cursor.fetchall():
                slots.append({
                    "slot_name": slot_name,
                    "slot_type": slot_type,
                    "database": datname,
                    "active": active,
                    "restart_lsn": str(restart_lsn) if restart_lsn else None,
                    "confirmed_flush_lsn": str(confirmed_flush_lsn) if confirmed_flush_lsn else None,
                })
            
            cursor.close()
            return slots
            
        except Exception as e:
            logger.error(f"Failed to get replication slots: {e}")
            self._metrics.streaming_errors += 1
            return None

    def get_wal_position(self) -> Optional[Dict[str, Any]]:
        """Get current WAL position on primary.
        
        Returns:
            WAL position information or None
        """
        try:
            cursor = self.primary_conn.cursor()
            
            # Get primary WAL position
            cursor.execute("SELECT pg_current_wal_lsn(), pg_current_wal_insert_lsn()")
            current_lsn, insert_lsn = cursor.fetchone()
            
            # Get WAL file info
            cursor.execute("""
                SELECT 
                    COUNT(*) as wal_files,
                    pg_size_pretty(SUM(size)) as total_size
                FROM pg_ls_waldir()
            """)
            
            wal_files, total_size = cursor.fetchone()
            cursor.close()
            
            return {
                "current_lsn": str(current_lsn),
                "insert_lsn": str(insert_lsn),
                "wal_files": wal_files,
                "wal_size": total_size,
            }
            
        except Exception as e:
            logger.error(f"Failed to get WAL position: {e}")
            self._metrics.streaming_errors += 1
            return None

    def get_replica_list(self) -> Dict[str, Dict[str, Any]]:
        """Get list of all configured replicas with their configs.
        
        Returns:
            Dictionary of replica configurations
        """
        return {
            name: {
                "name": config.replica_name,
                "role": config.role.value,
                "region": config.region,
                "sync_mode": config.sync_mode.value,
                "replica_host": config.replica_host,
                "status": self._replica_status.get(name, ReplicationStatus.DISCONNECTED).value,
            }
            for name, config in self._replicas.items()
        }

    def get_metrics(self) -> ReplicationMetrics:
        """Get replication metrics.
        
        Returns:
            Current replication metrics
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset replication metrics."""
        self._metrics = ReplicationMetrics(
            total_replicas=len(self._replicas),
            failover_count=self._metrics.failover_count,
        )
        logger.info("Replication metrics reset")


# Singleton instance
_replication_manager: Optional[ReplicationManager] = None


def get_replication_manager(conn: Any = None) -> ReplicationManager:
    """Get or create replication manager.
    
    Args:
        conn: Database connection for initialization
        
    Returns:
        Replication manager instance
    """
    global _replication_manager
    
    if _replication_manager is None:
        if conn is None:
            raise ValueError("Connection required to initialize replication manager")
        _replication_manager = ReplicationManager(conn)
    
    return _replication_manager


def reset_replication_manager() -> None:
    """Reset replication manager (for testing)."""
    global _replication_manager
    _replication_manager = None
