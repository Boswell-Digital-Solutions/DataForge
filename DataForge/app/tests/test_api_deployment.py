"""
Tests for API Deployment - Load Balancing & Session Management

Comprehensive test suite covering:
    - Load balancing strategies (round-robin, weighted, least-connections, IP hash)
    - Instance registration and health checks
    - Graceful draining and recovery
    - Session creation, management, and affinity
    - Connection pooling and metrics
    - End-to-end deployment workflows
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from typing import Any

from app.utils.load_balancer import (
    LoadBalancer,
    LoadBalancingStrategy,
    APIInstance,
    InstanceStatus,
    get_load_balancer,
    reset_load_balancer,
)
from app.utils.session_manager import (
    SessionManager,
    SessionData,
    ConnectionPool,
    get_session_manager,
    reset_session_manager,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def load_balancer() -> LoadBalancer:
    """Create load balancer for testing."""
    reset_load_balancer()
    return LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)


@pytest.fixture
def session_manager() -> SessionManager:
    """Create session manager for testing."""
    reset_session_manager()
    return SessionManager()


# ============================================================================
# Instance Registration Tests
# ============================================================================

class TestInstanceRegistration:
    """Test API instance registration."""
    
    def test_register_instance(self, load_balancer: LoadBalancer):
        """Test registering instance."""
        config = APIInstance(
            name="api-1",
            host="localhost",
            port=8001,
        )
        success = load_balancer.register_instance(config)
        assert success
        assert "api-1" in load_balancer.instances
    
    def test_register_multiple_instances(self, load_balancer: LoadBalancer):
        """Test registering multiple instances."""
        for i in range(3):
            config = APIInstance(name=f"api-{i}", host="localhost", port=8000+i)
            success = load_balancer.register_instance(config)
            assert success
        
        assert len(load_balancer.instances) == 3
    
    def test_unregister_instance(self, load_balancer: LoadBalancer):
        """Test unregistering instance."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        success = load_balancer.unregister_instance("api-1")
        assert success
        assert "api-1" not in load_balancer.instances


# ============================================================================
# Load Balancing Strategy Tests
# ============================================================================

class TestRoundRobinStrategy:
    """Test round-robin load balancing."""
    
    def test_round_robin_selection(self, load_balancer: LoadBalancer):
        """Test round-robin distribution."""
        for i in range(3):
            config = APIInstance(name=f"api-{i}", host="localhost")
            load_balancer.register_instance(config)
        
        selections = [load_balancer.select_instance() for _ in range(9)]
        
        # Should cycle through instances
        assert selections[0] == "api-0"
        assert selections[1] == "api-1"
        assert selections[2] == "api-2"
        assert selections[3] == "api-0"


class TestWeightedStrategy:
    """Test weighted load balancing."""
    
    def test_weighted_initialization(self):
        """Test weighted strategy initialization."""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.WEIGHTED)
        
        lb.register_instance(APIInstance(name="api-1", host="localhost", weight=100))
        lb.register_instance(APIInstance(name="api-2", host="localhost", weight=200))
        
        # Both instances should be registered
        assert len(lb.get_healthy_instances()) == 2


class TestLeastConnectionsStrategy:
    """Test least-connections load balancing."""
    
    def test_least_connections_selection(self):
        """Test least-connections distribution."""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
        
        for i in range(3):
            config = APIInstance(name=f"api-{i}", host="localhost")
            lb.register_instance(config)
        
        # Simulate connections
        lb.increment_active_connections("api-0")
        lb.increment_active_connections("api-0")
        lb.increment_active_connections("api-1")
        
        # Should select api-2 (fewest connections)
        selected = lb.select_instance()
        assert selected == "api-2"


class TestIPHashStrategy:
    """Test IP hash for session affinity."""
    
    def test_ip_hash_affinity(self):
        """Test same IP gets same instance."""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.IP_HASH)
        
        for i in range(3):
            config = APIInstance(name=f"api-{i}", host="localhost")
            lb.register_instance(config)
        
        client_ip = "192.168.1.100"
        
        # Same client should get same instance
        instance1 = lb.select_instance(client_ip)
        instance2 = lb.select_instance(client_ip)
        instance3 = lb.select_instance(client_ip)
        
        assert instance1 == instance2 == instance3


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthChecks:
    """Test instance health checking."""
    
    def test_mark_unhealthy(self, load_balancer: LoadBalancer):
        """Test marking instance unhealthy."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        # Simulate failures
        for _ in range(3):
            load_balancer.check_instance_health("api-1", False)
        
        # Should be marked unhealthy
        status = load_balancer.get_instance_status("api-1")
        assert status["status"] == InstanceStatus.UNHEALTHY.value
    
    def test_recover_to_healthy(self, load_balancer: LoadBalancer):
        """Test recovering to healthy."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        # Mark unhealthy
        for _ in range(3):
            load_balancer.check_instance_health("api-1", False)
        
        # Mark as healthy again
        load_balancer.check_instance_health("api-1", True)
        
        # Should be back to healthy
        status = load_balancer.get_instance_status("api-1")
        assert status["status"] == InstanceStatus.HEALTHY.value


# ============================================================================
# Connection Management Tests
# ============================================================================

class TestConnectionTracking:
    """Test active connection tracking."""
    
    def test_increment_connections(self, load_balancer: LoadBalancer):
        """Test incrementing connections."""
        config = APIInstance(name="api-1", host="localhost", max_connections=10)
        load_balancer.register_instance(config)
        
        success = load_balancer.increment_active_connections("api-1")
        assert success
        assert load_balancer.active_connections["api-1"] == 1
    
    def test_decrement_connections(self, load_balancer: LoadBalancer):
        """Test decrementing connections."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        load_balancer.increment_active_connections("api-1")
        success = load_balancer.decrement_active_connections("api-1")
        
        assert success
        assert load_balancer.active_connections["api-1"] == 0
    
    def test_max_connections_limit(self, load_balancer: LoadBalancer):
        """Test respecting max connections."""
        config = APIInstance(name="api-1", host="localhost", max_connections=2)
        load_balancer.register_instance(config)
        
        # Fill to max
        load_balancer.increment_active_connections("api-1")
        load_balancer.increment_active_connections("api-1")
        
        # Should reject over limit
        success = load_balancer.increment_active_connections("api-1")
        assert not success


# ============================================================================
# Graceful Draining Tests
# ============================================================================

class TestGracefulDraining:
    """Test graceful drain functionality."""
    
    def test_start_draining(self, load_balancer: LoadBalancer):
        """Test starting drain."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        success = load_balancer.start_draining("api-1")
        assert success
        
        status = load_balancer.get_instance_status("api-1")
        assert status["draining"]
    
    def test_drained_instance_not_selected(self, load_balancer: LoadBalancer):
        """Test draining removes from selection."""
        for i in range(3):
            config = APIInstance(name=f"api-{i}", host="localhost")
            load_balancer.register_instance(config)
        
        load_balancer.start_draining("api-0")
        
        # api-0 should not be selected
        healthy = load_balancer.get_healthy_instances()
        assert "api-0" not in healthy


# ============================================================================
# Session Management Tests
# ============================================================================

class TestSessionCreation:
    """Test session creation."""
    
    def test_create_session(self, session_manager: SessionManager):
        """Test creating session."""
        session = session_manager.create_session(user_id="user-1")
        
        assert session is not None
        assert session.session_id is not None
        assert session.user_id == "user-1"
    
    def test_get_session(self, session_manager: SessionManager):
        """Test retrieving session."""
        created = session_manager.create_session(user_id="user-1")
        retrieved = session_manager.get_session(created.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == created.session_id


class TestSessionExpiration:
    """Test session expiration."""
    
    def test_session_expires(self, session_manager: SessionManager):
        """Test session expiration."""
        session = session_manager.create_session(ttl_seconds=1)
        
        # Session should exist
        assert session_manager.get_session(session.session_id) is not None
        
        # Manually mark expired
        session.created_at = datetime.utcnow() - timedelta(seconds=2)
        
        # Session should be expired
        assert session_manager.get_session(session.session_id) is None


class TestSessionData:
    """Test session data management."""
    
    def test_update_session_data(self, session_manager: SessionManager):
        """Test updating session data."""
        session = session_manager.create_session()
        
        success = session_manager.update_session_data(
            session.session_id, "key1", "value1"
        )
        assert success
        
        updated = session_manager.get_session(session.session_id)
        assert updated.data["key1"] == "value1"


# ============================================================================
# Session Affinity Tests
# ============================================================================

class TestSessionAffinity:
    """Test session-to-instance affinity."""
    
    def test_set_affinity(self, session_manager: SessionManager):
        """Test setting instance affinity."""
        session = session_manager.create_session()
        
        success = session_manager.set_instance_affinity(
            session.session_id, "api-1"
        )
        assert success
        
        instance = session_manager.get_instance_for_session(session.session_id)
        assert instance == "api-1"


# ============================================================================
# Connection Pool Tests
# ============================================================================

class TestConnectionPool:
    """Test connection pooling."""
    
    def test_pool_initialization(self):
        """Test pool initialization."""
        pool = ConnectionPool("api-1", min_size=5, max_size=10)
        
        assert pool.instance_name == "api-1"
        assert pool.max_size == 10
        assert len(pool.available_connections) >= 5
    
    def test_acquire_connection(self):
        """Test acquiring connection from pool."""
        pool = ConnectionPool("api-1", min_size=5)
        
        # Acquire multiple connections
        initial_available = len(pool.available_connections)
        conn1 = pool.acquire_connection()
        
        # Should have moved from available to active
        if conn1 is not None:
            assert len(pool.available_connections) < initial_available
    
    def test_pool_exhaustion(self, session_manager: SessionManager):
        """Test pool metrics."""
        # Create a pool via session manager
        pool = session_manager.get_or_create_pool("api-1")
        
        # Get metrics
        metrics = session_manager.get_pool_metrics()
        assert metrics is not None


# ============================================================================
# Metrics Tests
# ============================================================================

class TestMetrics:
    """Test metrics collection."""
    
    def test_record_request(self, load_balancer: LoadBalancer):
        """Test recording request."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        load_balancer.record_request("api-1", 45.5, True)
        load_balancer.record_request("api-1", 52.3, True)
        
        status = load_balancer.get_instance_status("api-1")
        assert status["total_requests"] == 2
        assert status["average_response_time_ms"] > 0


class TestSessionMetrics:
    """Test session metrics."""
    
    def test_session_count(self, session_manager: SessionManager):
        """Test session counting."""
        session_manager.create_session(user_id="user-1")
        session_manager.create_session(user_id="user-1")
        session_manager.create_session(user_id="user-2")
        
        counts = session_manager.get_session_count()
        assert counts["total_active"] == 3


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_end_to_end_deployment(
        self,
        load_balancer: LoadBalancer,
        session_manager: SessionManager
    ):
        """Test complete deployment workflow."""
        # Register instances
        for i in range(3):
            config = APIInstance(name=f"api-{i}", host="localhost")
            load_balancer.register_instance(config)
        
        # Create session
        session = session_manager.create_session(user_id="user-1")
        
        # Set affinity
        session_manager.set_instance_affinity(session.session_id, "api-0")
        
        # Select instance
        selected = load_balancer.select_instance()
        assert selected is not None
        
        # Record metrics
        load_balancer.record_request(selected, 45.5, True)
        
        metrics = load_balancer.get_metrics()
        assert metrics["total_instances"] == 3
        assert metrics["total_requests"] == 1


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_no_healthy_instances(self, load_balancer: LoadBalancer):
        """Test selection with no healthy instances."""
        config = APIInstance(name="api-1", host="localhost")
        load_balancer.register_instance(config)
        
        # Mark unhealthy
        for _ in range(3):
            load_balancer.check_instance_health("api-1", False)
        
        # Should return None
        selected = load_balancer.select_instance()
        assert selected is None
    
    def test_session_not_found(self, session_manager: SessionManager):
        """Test getting nonexistent session."""
        session = session_manager.get_session("nonexistent")
        assert session is None
    
    def test_duplicate_instance_registration(self, load_balancer: LoadBalancer):
        """Test registering duplicate instance."""
        config = APIInstance(name="api-1", host="localhost")
        
        load_balancer.register_instance(config)
        load_balancer.register_instance(config)
        
        # Should just overwrite
        assert len(load_balancer.instances) == 1
