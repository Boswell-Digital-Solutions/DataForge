"""
Circuit Breaker Pattern Implementation for DataForge External API Calls

Prevents cascading failures by stopping requests to failing services.
Implements Closed → Open → Half-Open state machine with exponential backoff.

States:
- CLOSED: Normal operation, all requests pass through
- OPEN: Service failing, requests are rejected immediately
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery with limited requests


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker for external API calls.

    Configuration:
    - failure_threshold: Number of failures before opening (default: 5)
    - recovery_timeout: Seconds before attempting recovery (default: 60)
    - expected_exception: Exception type to catch (default: Exception)
    - half_open_max_calls: Max calls in half-open state (default: 1)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get number of consecutive failures."""
        return self._failure_count

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return False

        elapsed = (datetime.now(UTC) - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    async def _update_state(self) -> None:
        """Update circuit state based on failure count and time."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"🔄 [{self.name}] Recovery timeout passed, moving to HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    self._failure_count = 0

            elif self._state == CircuitState.HALF_OPEN:
                if self._failure_count > 0:
                    # Failure in half-open, reopen with exponential backoff
                    logger.error(f"❌ [{self.name}] Failed during recovery, reopening circuit")
                    self._state = CircuitState.OPEN
                    self._last_failure_time = datetime.now(UTC)
                    # Double the recovery timeout on each failure
                    self.recovery_timeout = int(self.recovery_timeout * 1.5)

                elif self._success_count >= self.half_open_max_calls:
                    # Successful recovery, close circuit
                    logger.info(f"✅ [{self.name}] Recovery successful, closing circuit")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    # Reset recovery timeout to original
                    self.recovery_timeout = max(
                        60, int(self.recovery_timeout / 1.5)
                    )

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(UTC)

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                f"🔴 [{self.name}] Circuit OPEN after {self._failure_count} failures "
                f"(threshold: {self.failure_threshold})"
            )

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            if self._failure_count > 0:
                logger.info(f"✅ [{self.name}] Failure count reset to 0")
            self._failure_count = 0

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with circuit breaker protection.

        Raises:
            CircuitBreakerError: If circuit is OPEN
            Original exception: If function raises expected exception
        """
        # Update state (may transition from OPEN → HALF_OPEN)
        await self._update_state()

        # Check if circuit is open
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Retry in {self.recovery_timeout}s."
            )

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self.record_success()
            return result

        except self.expected_exception as e:
            self.record_failure()
            logger.warning(
                f"⚠️  [{self.name}] Request failed (failures: {self._failure_count}/{self.failure_threshold}): {str(e)}"
            )
            raise

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED
        logger.info(f"🔄 [{self.name}] Circuit manually reset to CLOSED")

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "is_open": self.is_open,
        }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    Singleton pattern for application-wide access.
    """

    _instance: Optional["CircuitBreakerRegistry"] = None
    _breakers: Dict[str, CircuitBreaker] = {}

    def __new__(cls) -> "CircuitBreakerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        half_open_max_calls: int = 1,
    ) -> CircuitBreaker:
        """
        Register a new circuit breaker.

        Args:
            name: Unique identifier for the circuit breaker
            failure_threshold: Failures before opening
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
            half_open_max_calls: Max calls in half-open state

        Returns:
            CircuitBreaker instance
        """
        if name in self._breakers:
            logger.warning(f"Circuit breaker '{name}' already registered, returning existing")
            return self._breakers[name]

        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            half_open_max_calls=half_open_max_calls,
        )
        self._breakers[name] = breaker
        logger.info(f"📋 Registered circuit breaker: {name}")
        return breaker

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {name: breaker.get_status() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()

    def reset_by_name(self, name: str) -> bool:
        """Reset specific circuit breaker by name."""
        if name in self._breakers:
            self._breakers[name].reset()
            return True
        return False


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    return _registry


def circuit_breaker_decorator(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
):
    """
    Decorator for protecting functions with circuit breaker.

    Usage:
        @circuit_breaker_decorator("my_api", failure_threshold=3)
        async def call_external_api():
            ...
    """

    def decorator(func: Callable) -> Callable:
        registry = get_circuit_breaker_registry()
        breaker = registry.register(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # For sync functions, we need to handle differently
            # This is a simplified approach
            if breaker.is_open:
                raise CircuitBreakerError(
                    f"Circuit breaker '{name}' is OPEN. Service unavailable."
                )

            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except expected_exception as e:
                breaker.record_failure()
                logger.warning(f"⚠️  [{name}] Request failed: {str(e)}")
                raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
