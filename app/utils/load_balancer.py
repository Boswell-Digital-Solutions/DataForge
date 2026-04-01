"""
API Load Balancer with Round-Robin, Weighted, and Least-Connections Strategies

Implements multiple load balancing algorithms for distributing requests
across multiple API instances with health checking and failover support.

Strategies:
    - Round-Robin: Distribute equally across healthy instances
    - Weighted: Distribute based on instance capacity/weight
    - Least-Connections: Route to instance with fewest active connections
    - IP Hash: Route same client to same instance (session affinity)
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing algorithm."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    RANDOM = "random"


class InstanceStatus(str, Enum):
    """Health status of API instance."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"


@dataclass
class APIInstance:
    """Configuration for API instance in load balancer pool."""
    name: str
    host: str
    port: int = 8000
    weight: int = 100  # For weighted strategy (0-1000)
    max_connections: int = 1000
    health_check_path: str = "/health"
    health_check_interval_seconds: int = 5
    unhealthy_threshold: int = 3  # Failures before marking unhealthy
    healthy_threshold: int = 2    # Successes before marking healthy
    draining: bool = False  # Graceful shutdown mode
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.name or not self.host:
            raise ValueError("Instance name and host required")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Invalid port number")
        if not (0 <= self.weight <= 1000):
            raise ValueError("Weight must be 0-1000")
        if self.max_connections <= 0:
            raise ValueError("Max connections must be positive")
        return True


@dataclass
class InstanceMetrics:
    """Metrics for individual API instance."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: InstanceStatus = InstanceStatus.HEALTHY
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    consecutive_failures: int = 0
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "average_response_time_ms": self.average_response_time_ms,
            "error_rate": (
                self.failed_requests / self.total_requests 
                if self.total_requests > 0 else 0.0
            ),
            "consecutive_failures": self.consecutive_failures,
        }


class LoadBalancer:
    """
    Multi-strategy API load balancer with health checking and failover.
    
    Features:
        - Multiple load balancing strategies
        - Per-instance health monitoring
        - Connection tracking and limits
        - Graceful draining for deployments
        - Metrics collection and reporting
        - Automatic failover to healthy instances
    """
    
    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check_interval_seconds: int = 5,
        connection_timeout_seconds: int = 30,
    ):
        """
        Initialize load balancer.
        
        Args:
            strategy: Load balancing strategy
            health_check_interval_seconds: How often to check health
            connection_timeout_seconds: Connection idle timeout
        """
        self.strategy = strategy
        self.health_check_interval_seconds = health_check_interval_seconds
        self.connection_timeout_seconds = connection_timeout_seconds
        
        self.instances: Dict[str, APIInstance] = {}
        self.metrics: Dict[str, InstanceMetrics] = {}
        self.active_connections: Dict[str, int] = defaultdict(int)
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        
        # Round-robin state
        self.round_robin_index: int = 0
        
        # IP hash cache
        self.ip_hash_cache: Dict[str, str] = {}
    
    def register_instance(self, config: APIInstance) -> bool:
        """
        Register new API instance.
        
        Args:
            config: Instance configuration
            
        Returns:
            True if registration successful
        """
        try:
            config.validate()
            self.instances[config.name] = config
            self.metrics[config.name] = InstanceMetrics()
            self.active_connections[config.name] = 0
            logger.info(f"Registered instance: {config.name} ({config.host}:{config.port})")
            return True
        except Exception as e:
            logger.error(f"Failed to register instance {config.name}: {e}")
            return False
    
    def unregister_instance(self, instance_name: str) -> bool:
        """Remove instance from pool."""
        try:
            if instance_name in self.instances:
                del self.instances[instance_name]
                if instance_name in self.metrics:
                    del self.metrics[instance_name]
                if instance_name in self.active_connections:
                    del self.active_connections[instance_name]
                logger.info(f"Unregistered instance: {instance_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister instance {instance_name}: {e}")
            return False
    
    def get_healthy_instances(self) -> List[str]:
        """Get list of healthy instances available for routing."""
        healthy = []
        for name, metrics in self.metrics.items():
            if metrics.status == InstanceStatus.HEALTHY:
                healthy.append(name)
        return healthy
    
    def select_instance(self, client_ip: Optional[str] = None) -> Optional[str]:
        """
        Select instance for routing based on strategy.
        
        Args:
            client_ip: Client IP address (for IP hash strategy)
            
        Returns:
            Selected instance name or None if no healthy instances
        """
        healthy = self.get_healthy_instances()
        if not healthy:
            logger.warning("No healthy instances available")
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted_select(healthy)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy)
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash_select(healthy, client_ip)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            import random
            return random.choice(healthy)
        else:
            return healthy[0]
    
    def _round_robin_select(self, healthy_instances: List[str]) -> str:
        """Round-robin strategy."""
        selected = healthy_instances[self.round_robin_index % len(healthy_instances)]
        self.round_robin_index += 1
        return selected
    
    def _weighted_select(self, healthy_instances: List[str]) -> str:
        """Weighted selection by instance weight."""
        total_weight = sum(
            self.instances[name].weight for name in healthy_instances
        )
        
        if total_weight == 0:
            return healthy_instances[0]
        
        # Weighted round-robin
        target_weight = (self.round_robin_index % total_weight)
        self.round_robin_index += 1
        
        current_weight = 0
        for name in healthy_instances:
            current_weight += self.instances[name].weight
            if current_weight > target_weight:
                return name
        
        return healthy_instances[0]
    
    def _least_connections_select(self, healthy_instances: List[str]) -> str:
        """Select instance with fewest active connections."""
        return min(
            healthy_instances,
            key=lambda name: self.active_connections[name]
        )
    
    def _ip_hash_select(
        self,
        healthy_instances: List[str],
        client_ip: Optional[str]
    ) -> str:
        """IP hash for session affinity."""
        if not client_ip:
            return healthy_instances[0]
        
        # Check cache
        if client_ip in self.ip_hash_cache:
            cached = self.ip_hash_cache[client_ip]
            if cached in healthy_instances:
                return cached
        
        # Hash to instance
        hash_value = hash(client_ip) % len(healthy_instances)
        selected = healthy_instances[hash_value]
        self.ip_hash_cache[client_ip] = selected
        return selected
    
    def record_request(
        self,
        instance_name: str,
        response_time_ms: float,
        success: bool = True
    ) -> None:
        """Record request metrics for instance."""
        try:
            if instance_name not in self.metrics:
                return
            
            metrics = self.metrics[instance_name]
            metrics.total_requests += 1
            
            if success:
                metrics.successful_requests += 1
                metrics.consecutive_failures = 0
            else:
                metrics.failed_requests += 1
                metrics.consecutive_failures += 1
            
            # Track response times
            self.request_history[instance_name].append(response_time_ms)
            if len(self.request_history[instance_name]) > 1000:
                self.request_history[instance_name].pop(0)
            
            # Update averages
            recent = self.request_history[instance_name][-100:]
            metrics.average_response_time_ms = sum(recent) / len(recent)
            metrics.min_response_time_ms = min(recent)
            metrics.max_response_time_ms = max(recent)
        except Exception as e:
            logger.error(f"Error recording request for {instance_name}: {e}")
    
    def increment_active_connections(self, instance_name: str) -> bool:
        """Increment active connection count."""
        try:
            if instance_name not in self.instances:
                return False
            
            instance = self.instances[instance_name]
            if self.active_connections[instance_name] >= instance.max_connections:
                logger.warning(f"Instance {instance_name} at max connections")
                return False
            
            self.active_connections[instance_name] += 1
            self.metrics[instance_name].active_connections += 1
            return True
        except Exception as e:
            logger.error(f"Error incrementing connections for {instance_name}: {e}")
            return False
    
    def decrement_active_connections(self, instance_name: str) -> bool:
        """Decrement active connection count."""
        try:
            if instance_name not in self.instances:
                return False
            
            current = self.active_connections[instance_name]
            if current > 0:
                self.active_connections[instance_name] -= 1
                self.metrics[instance_name].active_connections -= 1
            return True
        except Exception as e:
            logger.error(f"Error decrementing connections for {instance_name}: {e}")
            return False
    
    def check_instance_health(self, instance_name: str, is_healthy: bool) -> None:
        """Update instance health status based on check."""
        try:
            if instance_name not in self.metrics:
                return
            
            metrics = self.metrics[instance_name]
            instance = self.instances[instance_name]
            
            metrics.last_health_check = datetime.now(UTC)
            
            if is_healthy:
                metrics.consecutive_failures = 0
                if metrics.status != InstanceStatus.HEALTHY:
                    # Check if ready to mark healthy
                    if metrics.consecutive_failures == 0:
                        metrics.status = InstanceStatus.HEALTHY
                        logger.info(f"Instance {instance_name} marked HEALTHY")
            else:
                metrics.consecutive_failures += 1
                metrics.health_check_failures += 1
                
                # Mark unhealthy if threshold exceeded
                if metrics.consecutive_failures >= instance.unhealthy_threshold:
                    if metrics.status == InstanceStatus.HEALTHY:
                        metrics.status = InstanceStatus.UNHEALTHY
                        logger.warning(f"Instance {instance_name} marked UNHEALTHY")
        except Exception as e:
            logger.error(f"Error checking health for {instance_name}: {e}")
    
    def start_draining(self, instance_name: str) -> bool:
        """Start graceful drain (stop accepting new connections)."""
        try:
            if instance_name not in self.instances:
                return False
            
            self.instances[instance_name].draining = True
            self.metrics[instance_name].status = InstanceStatus.DRAINING
            logger.info(f"Started draining instance {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error draining instance {instance_name}: {e}")
            return False
    
    def stop_draining(self, instance_name: str) -> bool:
        """Stop draining and mark instance ready."""
        try:
            if instance_name not in self.instances:
                return False
            
            self.instances[instance_name].draining = False
            self.metrics[instance_name].status = InstanceStatus.HEALTHY
            logger.info(f"Stopped draining instance {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error stopping drain for {instance_name}: {e}")
            return False
    
    def get_instance_status(self, instance_name: str) -> Optional[Dict[str, Any]]:
        """Get status of specific instance."""
        try:
            if instance_name not in self.instances:
                return None
            
            instance = self.instances[instance_name]
            metrics = self.metrics[instance_name]
            
            return {
                "name": instance_name,
                "host": instance.host,
                "port": instance.port,
                "weight": instance.weight,
                "draining": instance.draining,
                "status": metrics.status.value,
                "active_connections": metrics.active_connections,
                "max_connections": instance.max_connections,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "average_response_time_ms": metrics.average_response_time_ms,
                "error_rate": (
                    metrics.failed_requests / metrics.total_requests
                    if metrics.total_requests > 0 else 0.0
                ),
            }
        except Exception as e:
            logger.error(f"Error getting status for {instance_name}: {e}")
            return None
    
    def get_all_instances_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get status of all instances."""
        try:
            healthy_instances = []
            unhealthy_instances = []
            draining_instances = []
            
            for instance_name in self.instances:
                status = self.get_instance_status(instance_name)
                if not status:
                    continue
                
                if status["draining"]:
                    draining_instances.append(status)
                elif status["status"] == InstanceStatus.HEALTHY.value:
                    healthy_instances.append(status)
                else:
                    unhealthy_instances.append(status)
            
            return {
                "healthy": healthy_instances,
                "unhealthy": unhealthy_instances,
                "draining": draining_instances,
            }
        except Exception as e:
            logger.error(f"Error getting all instances status: {e}")
            return {"healthy": [], "unhealthy": [], "draining": []}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated load balancer metrics."""
        try:
            healthy = self.get_healthy_instances()
            total_instances = len(self.instances)
            total_connections = sum(self.active_connections.values())
            total_requests = sum(m.total_requests for m in self.metrics.values())
            total_failures = sum(m.failed_requests for m in self.metrics.values())
            
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "strategy": self.strategy.value,
                "total_instances": total_instances,
                "healthy_instances": len(healthy),
                "unhealthy_instances": total_instances - len(healthy),
                "total_active_connections": total_connections,
                "total_requests": total_requests,
                "total_failures": total_failures,
                "error_rate": (
                    total_failures / total_requests
                    if total_requests > 0 else 0.0
                ),
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}


# Global singleton instance
_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer(
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
) -> LoadBalancer:
    """
    Get or create global load balancer instance.
    
    Args:
        strategy: Load balancing strategy
        
    Returns:
        Global LoadBalancer instance
    """
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(strategy=strategy)
    return _load_balancer


def reset_load_balancer() -> None:
    """Reset global load balancer (for testing)."""
    global _load_balancer
    _load_balancer = None
