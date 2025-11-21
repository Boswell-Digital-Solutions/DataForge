"""
Tests for Cache Replication & Failover System

Comprehensive test suite covering:
    - Replica registration and management
    - Replication lag tracking
    - Health checks and failover state machine
    - Replica selection algorithm
    - Sentinel integration
    - Error handling and edge cases
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from typing import Any

from app.utils.cache_replication import (
    CacheReplicationManager,
    ReplicaConfig,
    ReplicaRole,
    ReplicationMode,
    ReplicationStatus,
    get_cache_replication_manager,
    reset_cache_replication_manager,
)
from app.utils.cache_failover import (
    CacheFailoverManager,
    FailoverConfig,
    FailoverMode,
    FailoverState,
    FailoverReason,
    get_cache_failover_manager,
    reset_cache_failover_manager,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_conn() -> MagicMock:
    """Mock Redis connection."""
    conn = MagicMock()
    conn.ping.return_value = True
    conn.info.return_value = {
        "role": "master",
        "connected_slaves": 2,
        "master_replid": "0" * 40,
        "replication_backlog_bytes": 1024,
    }
    return conn


@pytest.fixture
def mock_sentinel_conn() -> MagicMock:
    """Mock Redis Sentinel connection."""
    conn = MagicMock()
    conn.ping.return_value = True
    return conn


@pytest.fixture
def replication_manager(mock_redis_conn: MagicMock) -> CacheReplicationManager:
    """Create cache replication manager for testing."""
    reset_cache_replication_manager()
    mgr = CacheReplicationManager(
        primary_conn=mock_redis_conn,
        service_name="mymaster",
    )
    return mgr


@pytest.fixture
def failover_manager(replication_manager: CacheReplicationManager) -> CacheFailoverManager:
    """Create cache failover manager for testing."""
    reset_cache_failover_manager()
    config = FailoverConfig(
        primary_host="localhost",
        primary_port=6379,
        failover_mode=FailoverMode.AUTOMATIC,
        failure_threshold=3,
    )
    mgr = CacheFailoverManager(config=config, replication_manager=replication_manager)
    return mgr


# ============================================================================
# ReplicaConfig Tests
# ============================================================================

class TestReplicaConfig:
    """Test suite for ReplicaConfig validation."""
    
    def test_valid_config(self):
        """Test valid replica configuration."""
        config = ReplicaConfig(
            name="replica-1",
            host="localhost",
            port=6380,
            role=ReplicaRole.REPLICA,
        )
        assert config.validate()
        assert config.name == "replica-1"
        assert config.port == 6380
    
    def test_invalid_config_missing_name(self):
        """Test config validation with missing name."""
        config = ReplicaConfig(name="", host="localhost")
        with pytest.raises(ValueError):
            config.validate()
    
    def test_invalid_config_bad_port(self):
        """Test config validation with invalid port."""
        config = ReplicaConfig(name="replica-1", host="localhost", port=99999)
        with pytest.raises(ValueError):
            config.validate()


# ============================================================================
# Replica Registration & Management Tests
# ============================================================================

class TestReplicaRegistration:
    """Test replica registration and management."""
    
    def test_register_replica(self, replication_manager: CacheReplicationManager):
        """Test registering a new replica."""
        config = ReplicaConfig(
            name="replica-1",
            host="localhost",
            port=6380,
            role=ReplicaRole.REPLICA,
        )
        success = replication_manager.register_replica(config)
        assert success
        assert "replica-1" in replication_manager.replicas
    
    def test_register_multiple_replicas(self, replication_manager: CacheReplicationManager):
        """Test registering multiple replicas."""
        for i in range(3):
            config = ReplicaConfig(
                name=f"replica-{i}",
                host="localhost",
                port=6380 + i,
            )
            success = replication_manager.register_replica(config)
            assert success
        
        assert len(replication_manager.replicas) == 3
    
    def test_unregister_replica(self, replication_manager: CacheReplicationManager):
        """Test unregistering a replica."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        
        success = replication_manager.unregister_replica("replica-1")
        assert success
        assert "replica-1" not in replication_manager.replicas
    
    def test_unregister_nonexistent_replica(self, replication_manager: CacheReplicationManager):
        """Test unregistering a replica that doesn't exist."""
        success = replication_manager.unregister_replica("nonexistent")
        assert not success


# ============================================================================
# Replica Status & Lag Tests
# ============================================================================

class TestReplicaStatus:
    """Test replica status and lag tracking."""
    
    def test_get_replica_status(self, replication_manager: CacheReplicationManager):
        """Test getting replica status."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        
        status = replication_manager.get_replica_status("replica-1")
        assert status is not None
        assert status["name"] == "replica-1"
        assert status["host"] == "localhost"
        assert status["role"] == "replica"
    
    def test_get_nonexistent_replica_status(self, replication_manager: CacheReplicationManager):
        """Test getting status of nonexistent replica."""
        status = replication_manager.get_replica_status("nonexistent")
        assert status is None
    
    def test_replica_lag_tracking(self, replication_manager: CacheReplicationManager):
        """Test replica lag tracking."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        
        # Set simulated lag
        replication_manager.replica_status["replica-1"]["lag_ms"] = 50.5
        
        lag_ms = replication_manager.get_replica_lag_ms("replica-1")
        assert lag_ms == 50.5
    
    def test_get_all_replica_lags(self, replication_manager: CacheReplicationManager):
        """Test getting lags for all replicas."""
        for i in range(3):
            config = ReplicaConfig(name=f"replica-{i}", host="localhost")
            replication_manager.register_replica(config)
            replication_manager.replica_status[f"replica-{i}"]["lag_ms"] = 10.0 * i
        
        lags = replication_manager.get_all_replica_lags()
        assert len(lags) == 3
        assert lags["replica-0"] == 0.0
        assert lags["replica-1"] == 10.0
        assert lags["replica-2"] == 20.0


# ============================================================================
# Replication Mode Tests
# ============================================================================

class TestReplicationMode:
    """Test replication mode management."""
    
    def test_set_replication_mode(self, replication_manager: CacheReplicationManager):
        """Test changing replication mode."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        
        success = replication_manager.set_replication_mode(
            "replica-1", 
            ReplicationMode.SYNCHRONOUS
        )
        assert success
        assert replication_manager.replicas["replica-1"].replication_mode == ReplicationMode.SYNCHRONOUS
    
    def test_set_mode_for_nonexistent_replica(self, replication_manager: CacheReplicationManager):
        """Test setting mode for nonexistent replica."""
        success = replication_manager.set_replication_mode(
            "nonexistent",
            ReplicationMode.SYNCHRONOUS
        )
        assert not success


# ============================================================================
# Replica Promotion Tests
# ============================================================================

class TestReplicaPromotion:
    """Test replica promotion (failover)."""
    
    def test_promote_replica_to_primary(self, replication_manager: CacheReplicationManager):
        """Test promoting a replica to primary."""
        config = ReplicaConfig(
            name="replica-1",
            host="localhost",
            role=ReplicaRole.REPLICA,
        )
        replication_manager.register_replica(config)
        replication_manager.replica_status["replica-1"]["lag_ms"] = 1.5
        
        success = replication_manager.promote_replica_to_primary("replica-1")
        assert success
        assert replication_manager.replicas["replica-1"].role == ReplicaRole.PRIMARY
    
    def test_promote_lagged_replica_fails(self, replication_manager: CacheReplicationManager):
        """Test promoting replica with too much lag fails."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        replication_manager.replica_status["replica-1"]["lag_ms"] = 10000.0  # 10 seconds
        
        success = replication_manager.promote_replica_to_primary("replica-1")
        assert not success


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthChecks:
    """Test health checking and failover triggering."""
    
    def test_primary_health_check_success(
        self,
        failover_manager: CacheFailoverManager,
        mock_redis_conn: MagicMock
    ):
        """Test successful primary health check."""
        is_healthy = failover_manager.check_primary_health(mock_redis_conn)
        assert is_healthy
        assert len(failover_manager.failure_history) == 0
    
    def test_primary_health_check_failure(
        self,
        failover_manager: CacheFailoverManager,
        mock_redis_conn: MagicMock
    ):
        """Test primary health check failure tracking."""
        mock_redis_conn.ping.side_effect = Exception("Connection failed")
        
        for _ in range(3):
            is_healthy = failover_manager.check_primary_health(mock_redis_conn)
            assert not is_healthy
        
        assert len(failover_manager.failure_history) == 3
    
    def test_failover_threshold_not_met(self, failover_manager: CacheFailoverManager):
        """Test failover not triggered below threshold."""
        failover_manager.failure_history = [datetime.utcnow()]
        assert not failover_manager.should_failover()
    
    def test_failover_threshold_met(self, failover_manager: CacheFailoverManager):
        """Test failover triggered at threshold."""
        now = datetime.utcnow()
        failover_manager.failure_history = [
            now,
            now - timedelta(seconds=1),
            now - timedelta(seconds=2),
        ]
        assert failover_manager.should_failover()


# ============================================================================
# Failover State Machine Tests
# ============================================================================

class TestFailoverStateMachine:
    """Test failover state transitions."""
    
    def test_initial_state_healthy(self, failover_manager: CacheFailoverManager):
        """Test initial state is HEALTHY."""
        assert failover_manager.metrics.current_state == FailoverState.HEALTHY
    
    def test_state_transition_to_failed(self, failover_manager: CacheFailoverManager):
        """Test state transition on failure."""
        failover_manager.metrics.current_state = FailoverState.PRIMARY_FAILED
        assert failover_manager.metrics.current_state == FailoverState.PRIMARY_FAILED
    
    def test_failover_in_progress_state(self, failover_manager: CacheFailoverManager):
        """Test failover in progress state."""
        failover_manager.metrics.current_state = FailoverState.FAILOVER_IN_PROGRESS
        assert failover_manager.metrics.current_state == FailoverState.FAILOVER_IN_PROGRESS


# ============================================================================
# Replica Selection Tests
# ============================================================================

class TestReplicaSelection:
    """Test replica selection algorithm for promotion."""
    
    def test_select_promotion_candidate_by_lag(
        self,
        replication_manager: CacheReplicationManager,
        failover_manager: CacheFailoverManager
    ):
        """Test selecting replica with lowest lag."""
        # Register replicas with different lags
        for i in range(3):
            config = ReplicaConfig(name=f"replica-{i}", host="localhost")
            replication_manager.register_replica(config)
            replication_manager.replica_status[f"replica-{i}"]["lag_ms"] = float(i * 10)
            replication_manager.replica_status[f"replica-{i}"]["status"] = ReplicationStatus.CONNECTED
        
        # Mock connectivity check
        replication_manager.check_replica_connectivity = MagicMock(return_value=True)
        
        selected = failover_manager.select_promotion_candidate()
        assert selected == "replica-0"  # Lowest lag
    
    def test_select_promotion_candidate_none_available(
        self,
        replication_manager: CacheReplicationManager,
        failover_manager: CacheFailoverManager
    ):
        """Test selection when no candidates available."""
        replication_manager.check_replica_connectivity = MagicMock(return_value=False)
        selected = failover_manager.select_promotion_candidate()
        assert selected is None


# ============================================================================
# Failover Workflow Tests
# ============================================================================

class TestFailoverWorkflow:
    """Test complete failover workflows."""
    
    def test_initiate_failover_success(
        self,
        replication_manager: CacheReplicationManager,
        failover_manager: CacheFailoverManager
    ):
        """Test successful failover initiation."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        replication_manager.replica_status["replica-1"]["status"] = ReplicationStatus.CONNECTED
        replication_manager.check_replica_connectivity = MagicMock(return_value=True)
        
        success = failover_manager.initiate_failover(FailoverReason.PRIMARY_UNAVAILABLE)
        assert success
        assert failover_manager.metrics.failover_count == 1
        assert failover_manager.metrics.current_state == FailoverState.FAILOVER_COMPLETE
    
    def test_initiate_failover_no_candidates(
        self,
        replication_manager: CacheReplicationManager,
        failover_manager: CacheFailoverManager
    ):
        """Test failover fails when no candidates available."""
        replication_manager.check_replica_connectivity = MagicMock(return_value=False)
        
        success = failover_manager.initiate_failover(FailoverReason.PRIMARY_UNAVAILABLE)
        assert not success
    
    def test_failover_not_allowed_when_in_progress(
        self,
        failover_manager: CacheFailoverManager
    ):
        """Test failover cannot start if already in progress."""
        failover_manager.metrics.current_state = FailoverState.FAILOVER_IN_PROGRESS
        
        success = failover_manager.initiate_failover(FailoverReason.PRIMARY_UNAVAILABLE)
        assert not success


# ============================================================================
# Recovery Tests
# ============================================================================

class TestRecovery:
    """Test primary recovery procedures."""
    
    def test_begin_recovery(self, failover_manager: CacheFailoverManager):
        """Test beginning recovery of old primary."""
        success = failover_manager.begin_recovery("old-primary")
        assert success
        assert failover_manager.metrics.recovery_attempts == 1
        assert failover_manager.metrics.current_state == FailoverState.HEALTHY


# ============================================================================
# Readonly Mode Tests
# ============================================================================

class TestReadonlyMode:
    """Test readonly mode for graceful degradation."""
    
    def test_enable_readonly_mode(self, failover_manager: CacheFailoverManager):
        """Test enabling readonly mode."""
        success = failover_manager.set_readonly_mode(True)
        assert success
        assert failover_manager.metrics.readonly_mode_enabled
    
    def test_disable_readonly_mode(self, failover_manager: CacheFailoverManager):
        """Test disabling readonly mode."""
        success = failover_manager.set_readonly_mode(False)
        assert success
        assert not failover_manager.metrics.readonly_mode_enabled


# ============================================================================
# Metrics Tests
# ============================================================================

class TestMetrics:
    """Test metrics collection and reporting."""
    
    def test_replication_metrics(self, replication_manager: CacheReplicationManager):
        """Test replication metrics."""
        for i in range(3):
            config = ReplicaConfig(name=f"replica-{i}", host="localhost")
            replication_manager.register_replica(config)
        
        metrics = replication_manager.get_metrics()
        assert metrics["total_replicas"] == 3
        assert "timestamp" in metrics
    
    def test_failover_metrics(self, failover_manager: CacheFailoverManager):
        """Test failover metrics."""
        metrics = failover_manager.get_metrics()
        assert metrics["current_state"] == FailoverState.HEALTHY.value
        assert metrics["failover_count"] == 0


# ============================================================================
# Singleton Tests
# ============================================================================

class TestSingleton:
    """Test singleton pattern for managers."""
    
    def test_replication_manager_singleton(self, mock_redis_conn: MagicMock):
        """Test replication manager singleton."""
        reset_cache_replication_manager()
        mgr1 = get_cache_replication_manager(mock_redis_conn)
        mgr2 = get_cache_replication_manager(mock_redis_conn)
        assert mgr1 is mgr2
    
    def test_failover_manager_singleton(self, mock_redis_conn: MagicMock):
        """Test failover manager singleton."""
        reset_cache_failover_manager()
        config = FailoverConfig()
        mgr1 = get_cache_failover_manager(config)
        mgr2 = get_cache_failover_manager(config)
        assert mgr1 is mgr2


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_end_to_end_replica_registration_and_failover(
        self,
        replication_manager: CacheReplicationManager,
        failover_manager: CacheFailoverManager,
        mock_redis_conn: MagicMock
    ):
        """Test complete workflow from registration to failover."""
        # Register replicas
        for i in range(2):
            config = ReplicaConfig(name=f"replica-{i}", host="localhost")
            replication_manager.register_replica(config)
        
        # Mock connectivity
        replication_manager.check_replica_connectivity = MagicMock(return_value=True)
        
        # Verify registration
        assert len(replication_manager.replicas) == 2
        
        # Trigger failover
        success = failover_manager.initiate_failover(FailoverReason.PRIMARY_UNAVAILABLE)
        assert success
        assert failover_manager.metrics.current_state == FailoverState.FAILOVER_COMPLETE


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_register_duplicate_replica(
        self,
        replication_manager: CacheReplicationManager
    ):
        """Test registering replica with duplicate name."""
        config = ReplicaConfig(name="replica-1", host="localhost")
        replication_manager.register_replica(config)
        replication_manager.register_replica(config)
        # Should just overwrite
        assert len(replication_manager.replicas) == 1
    
    def test_promotion_with_nonexistent_replica(
        self,
        replication_manager: CacheReplicationManager
    ):
        """Test promoting nonexistent replica."""
        success = replication_manager.promote_replica_to_primary("nonexistent")
        assert not success
    
    def test_get_metrics_with_no_replicas(
        self,
        replication_manager: CacheReplicationManager
    ):
        """Test metrics with no replicas."""
        metrics = replication_manager.get_metrics()
        assert metrics["total_replicas"] == 0
    
    def test_failover_state_recovery(self, failover_manager: CacheFailoverManager):
        """Test state recovery after failed failover."""
        failover_manager.metrics.current_state = FailoverState.PRIMARY_FAILED
        failover_manager.begin_recovery("old-primary")
        assert failover_manager.metrics.current_state == FailoverState.HEALTHY
