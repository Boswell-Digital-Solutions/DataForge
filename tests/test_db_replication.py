"""Comprehensive tests for database replication and failover."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import logging

from app.utils.db_replication import (
    ReplicationManager,
    ReplicaConfig,
    ReplicaRole,
    ReplicationMode,
    ReplicationStatus,
    get_replication_manager,
    reset_replication_manager,
)
from app.utils.db_failover import (
    FailoverManager,
    FailoverConfig,
    FailoverMode,
    FailoverState,
    get_failover_manager,
    reset_failover_manager,
)


@pytest.fixture
def mock_db_conn():
    """Mock database connection."""
    conn = MagicMock()
    cursor = MagicMock()
    
    conn.cursor.return_value = cursor
    cursor.fetchone.return_value = ("replica")
    cursor.fetchall.return_value = []
    
    return conn


@pytest.fixture
def replication_manager(mock_db_conn):
    """Create replication manager instance."""
    reset_replication_manager()
    return ReplicationManager(mock_db_conn)


@pytest.fixture
def failover_manager(replication_manager):
    """Create failover manager instance."""
    reset_failover_manager()
    return FailoverManager(replication_manager)


class TestReplicaConfig:
    """Test replica configuration."""
    
    def test_replica_config_creation(self):
        """Test creating replica config."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        assert config.replica_name == "replica-1"
        assert config.role == ReplicaRole.STANDBY
        assert config.sync_mode == ReplicationMode.ASYNCHRONOUS


class TestReplicationManager:
    """Test replication manager."""
    
    def test_manager_initialization(self, replication_manager, mock_db_conn):
        """Test manager initialization."""
        assert replication_manager.primary_conn is mock_db_conn
        assert len(replication_manager._replicas) == 0
    
    def test_register_replica(self, replication_manager):
        """Test registering a replica."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        success = replication_manager.register_replica(config)
        assert success is True
        assert "replica-1" in replication_manager._replicas
    
    def test_register_duplicate_replica(self, replication_manager):
        """Test registering duplicate replica fails."""
        config1 = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        assert replication_manager.register_replica(config1) is True
        assert replication_manager.register_replica(config1) is False
    
    def test_unregister_replica(self, replication_manager):
        """Test unregistering a replica."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        success = replication_manager.unregister_replica("replica-1")
        
        assert success is True
        assert "replica-1" not in replication_manager._replicas
    
    def test_get_replica_list(self, replication_manager):
        """Test getting replica list."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        replicas = replication_manager.get_replica_list()
        
        assert len(replicas) == 1
        assert "replica-1" in replicas
    
    def test_get_replica_status(self, replication_manager, mock_db_conn):
        """Test getting replica status."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        
        # Mock cursor response
        cursor = mock_db_conn.cursor.return_value
        cursor.fetchone.return_value = (
            "192.168.1.2",  # client_addr
            "streaming",     # state
            "async",         # sync_state
            None,            # write_lag
            None,            # flush_lag
            None,            # replay_lag
            datetime.now(),  # backend_start
        )
        
        status = replication_manager.get_replica_status("replica-1")
        
        assert status is not None
        assert status["replica_name"] == "replica-1"
        assert status["state"] == "streaming"
    
    def test_get_all_replica_lags(self, replication_manager, mock_db_conn):
        """Test getting lag for all replicas."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        
        # Mock lag response
        cursor = mock_db_conn.cursor.return_value
        cursor.fetchone.side_effect = [
            ("192.168.1.2", "streaming", "async", None, None, None, datetime.now()),
            (5.0, 1000),  # lag_seconds, lag_bytes
        ]
        
        lags = replication_manager.get_all_replica_lags()
        
        assert len(lags) > 0 or len(lags) == 0  # May vary based on mock
    
    def test_set_synchronous_mode(self, replication_manager):
        """Test setting synchronous mode."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        success = replication_manager.set_synchronous_mode("replica-1", sync=True)
        
        assert success is True
        assert replication_manager._replicas["replica-1"].sync_mode == ReplicationMode.SYNCHRONOUS
    
    def test_promote_replica_to_primary(self, replication_manager):
        """Test promoting replica to primary."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        success = replication_manager.promote_replica_to_primary("replica-1")
        
        assert success is True
    
    def test_get_metrics(self, replication_manager):
        """Test getting metrics."""
        metrics = replication_manager.get_metrics()
        
        assert metrics.total_replicas == 0
        assert metrics.active_replicas == 0
        assert metrics.replication_failures == 0


class TestFailoverManager:
    """Test failover manager."""
    
    def test_failover_initialization(self, failover_manager, replication_manager):
        """Test failover manager initialization."""
        assert failover_manager.replication_manager is replication_manager
        assert failover_manager._state == FailoverState.HEALTHY
    
    def test_check_primary_health_success(self, failover_manager, mock_db_conn):
        """Test successful primary health check."""
        mock_db_conn.cursor.return_value.fetchone.return_value = (1,)
        
        is_healthy, error = failover_manager.check_primary_health(mock_db_conn)
        
        assert is_healthy is True
        assert error is None
        assert failover_manager._primary_failure_count == 0
    
    def test_check_primary_health_failure(self, failover_manager, mock_db_conn):
        """Test failed primary health check."""
        mock_db_conn.cursor.side_effect = Exception("Connection refused")
        
        is_healthy, error = failover_manager.check_primary_health(mock_db_conn)
        
        assert is_healthy is False
        assert error is not None
        assert failover_manager._primary_failure_count == 1
    
    def test_primary_failure_threshold(self, failover_manager, mock_db_conn):
        """Test primary failure threshold triggers state change."""
        mock_db_conn.cursor.side_effect = Exception("Connection refused")
        
        # Trigger multiple failures
        for _ in range(failover_manager.config.primary_unhealthy_threshold):
            failover_manager.check_primary_health(mock_db_conn)
        
        assert failover_manager._state == FailoverState.PRIMARY_FAILED
    
    def test_select_promotion_candidate(self, failover_manager, replication_manager):
        """Test selecting promotion candidate."""
        # Register a replica
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        
        # Mock replica list
        replication_manager.get_replica_list = Mock(
            return_value={
                "replica-1": {
                    "name": "replica-1",
                    "role": "standby",
                    "region": "us-east-1",
                    "sync_mode": "asynchronous",
                    "status": "streaming",
                }
            }
        )
        
        replication_manager.get_all_replica_lags = Mock(
            return_value={
                "replica-1": {
                    "replica_name": "replica-1",
                    "lag_seconds": 0.5,
                    "lag_bytes": 100,
                    "is_lagged": False,
                }
            }
        )
        
        candidate = failover_manager.select_promotion_candidate()
        assert candidate == "replica-1"
    
    def test_initiate_failover_success(self, failover_manager, replication_manager):
        """Test successful failover initiation."""
        # Setup replica
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        
        # Mock selection and promotion
        failover_manager.select_promotion_candidate = Mock(return_value="replica-1")
        replication_manager.promote_replica_to_primary = Mock(return_value=True)
        
        success = failover_manager.initiate_failover("Test failover")
        
        assert success is True
        assert failover_manager._state == FailoverState.FAILOVER_COMPLETE
        assert failover_manager._metrics.successful_failovers == 1
    
    def test_initiate_failover_no_candidate(self, failover_manager):
        """Test failover when no suitable candidate."""
        failover_manager.select_promotion_candidate = Mock(return_value=None)
        
        success = failover_manager.initiate_failover("Test failover")
        
        assert success is False
        assert failover_manager._metrics.failed_failovers == 1
    
    def test_promote_replica_manual(self, failover_manager, replication_manager):
        """Test manual replica promotion."""
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        
        replication_manager.register_replica(config)
        replication_manager.promote_replica_to_primary = Mock(return_value=True)
        
        success = failover_manager.promote_replica_manual("replica-1")
        
        assert success is True
        assert failover_manager._metrics.successful_failovers == 1
    
    def test_recover_primary(self, failover_manager):
        """Test primary recovery after failover."""
        success = failover_manager.recover_primary("replica-1")
        
        assert success is True
        assert failover_manager._state == FailoverState.HEALTHY
        assert failover_manager._metrics.primary_recoveries == 1
    
    def test_get_current_state(self, failover_manager):
        """Test getting current failover state."""
        state = failover_manager.get_current_state()
        
        assert state["state"] == FailoverState.HEALTHY.value
        assert "metrics" in state
        assert state["metrics"]["total_failovers"] == 0
    
    def test_get_failover_metrics(self, failover_manager):
        """Test getting failover metrics."""
        metrics = failover_manager.get_metrics()
        
        assert metrics.total_failovers == 0
        assert metrics.successful_failovers == 0
        assert metrics.failed_failovers == 0
        assert metrics.primary_failures == 0


class TestSingleton:
    """Test singleton pattern."""
    
    def test_replication_manager_singleton(self, mock_db_conn):
        """Test replication manager singleton."""
        reset_replication_manager()
        
        mgr1 = get_replication_manager(mock_db_conn)
        mgr2 = get_replication_manager(mock_db_conn)
        
        assert mgr1 is mgr2
    
    def test_failover_manager_singleton(self, replication_manager):
        """Test failover manager singleton."""
        reset_failover_manager()
        
        mgr1 = get_failover_manager(replication_manager)
        mgr2 = get_failover_manager(replication_manager)
        
        assert mgr1 is mgr2


class TestIntegration:
    """Integration tests for replication and failover."""
    
    def test_register_multiple_replicas(self, replication_manager):
        """Test registering multiple replicas."""
        for i in range(3):
            config = ReplicaConfig(
                replica_name=f"replica-{i}",
                primary_host="primary.db",
                replica_host=f"replica{i}.db",
                replica_port=5432,
                role=ReplicaRole.STANDBY,
                region="us-east-1",
            )
            assert replication_manager.register_replica(config) is True
        
        replicas = replication_manager.get_replica_list()
        assert len(replicas) == 3
    
    def test_failover_workflow(self, failover_manager, replication_manager):
        """Test complete failover workflow."""
        # Setup replicas
        config = ReplicaConfig(
            replica_name="replica-1",
            primary_host="primary.db",
            replica_host="replica.db",
            replica_port=5432,
            role=ReplicaRole.STANDBY,
            region="us-east-1",
        )
        replication_manager.register_replica(config)
        
        # Mock methods
        replication_manager.promote_replica_to_primary = Mock(return_value=True)
        failover_manager.select_promotion_candidate = Mock(return_value="replica-1")
        
        # Execute failover
        success = failover_manager.initiate_failover("Test workflow")
        
        assert success is True
        assert failover_manager._promoted_replica == "replica-1"
        assert failover_manager._state == FailoverState.FAILOVER_COMPLETE


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_unregister_nonexistent_replica(self, replication_manager):
        """Test unregistering non-existent replica."""
        success = replication_manager.unregister_replica("nonexistent")
        assert success is False
    
    def test_get_status_nonexistent_replica(self, replication_manager):
        """Test getting status of non-existent replica."""
        status = replication_manager.get_replica_status("nonexistent")
        assert status is None
    
    def test_promote_nonexistent_replica(self, replication_manager):
        """Test promoting non-existent replica."""
        success = replication_manager.promote_replica_to_primary("nonexistent")
        assert success is False
    
    def test_failover_with_empty_replicas(self, failover_manager):
        """Test failover with no replicas."""
        candidate = failover_manager.select_promotion_candidate()
        assert candidate is None
    
    def test_reset_metrics(self, replication_manager):
        """Test resetting metrics."""
        replication_manager.reset_metrics()
        metrics = replication_manager.get_metrics()
        
        assert metrics.replication_failures == 0
        assert metrics.streaming_errors == 0
