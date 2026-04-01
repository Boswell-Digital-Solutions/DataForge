"""
Performance Monitoring and Metrics

Provides timing decorators and slow query logging for performance optimization.
Tracks query execution times and logs queries exceeding configured thresholds.
"""
import functools
import logging
import time
from typing import Callable, Any, TypeVar, Optional, Dict, List
from datetime import datetime, UTC
import json

logger = logging.getLogger(__name__)

# Configuration
SLOW_QUERY_THRESHOLD_MS = 500  # Log queries taking longer than 500ms

T = TypeVar("T")

# Global metrics storage (can be extended for real monitoring systems)
metrics_data: Dict[str, Any] = {
    "total_queries": 0,
    "slow_queries": 0,
    "total_query_time_ms": 0.0,
    "slowest_queries": [],  # Top 10 slowest queries
}


def track_query_timing(query_name: str, threshold_ms: int = SLOW_QUERY_THRESHOLD_MS) -> Callable:
    """
    Decorator to track query execution time and log slow queries.

    Args:
        query_name: Name of the query for logging
        threshold_ms: Threshold in milliseconds to consider a query "slow"

    Example:
        @track_query_timing("get_projects", threshold_ms=300)
        def get_projects(db: Session, user_id: int):
            # database operation
            return results
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                _record_query_metric(query_name, elapsed_ms, threshold_ms)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)  # type: ignore
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                _record_query_metric(query_name, elapsed_ms, threshold_ms)

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def _record_query_metric(query_name: str, elapsed_ms: float, threshold_ms: int) -> None:
    """Record query metrics and log if slow."""
    metrics_data["total_queries"] = int(metrics_data["total_queries"]) + 1  # type: ignore
    metrics_data["total_query_time_ms"] = float(metrics_data["total_query_time_ms"]) + elapsed_ms  # type: ignore

    if elapsed_ms > threshold_ms:
        metrics_data["slow_queries"] = int(metrics_data["slow_queries"]) + 1  # type: ignore
        logger.warning(
            f"SLOW QUERY: {query_name} took {elapsed_ms:.2f}ms (threshold: {threshold_ms}ms)"
        )

        # Track top 10 slowest queries
        query_record = {
            "query": query_name,
            "duration_ms": elapsed_ms,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        slowest: List[Dict[str, Any]] = metrics_data["slowest_queries"]  # type: ignore
        slowest.append(query_record)
        metrics_data["slowest_queries"] = sorted(
            slowest,
            key=lambda x: x["duration_ms"],
            reverse=True,
        )[:10]
    else:
        logger.debug(f"Query: {query_name} took {elapsed_ms:.2f}ms")


def get_query_metrics() -> Dict[str, Any]:
    """
    Get current query performance metrics.

    Returns:
        Dictionary with:
        - total_queries: Total number of tracked queries
        - slow_queries: Count of queries exceeding threshold
        - avg_query_time_ms: Average query execution time
        - slowest_queries: Top 10 slowest queries with timing
        - slow_query_percentage: Percentage of queries that were slow
    """
    total = int(metrics_data["total_queries"])  # type: ignore
    total_time = float(metrics_data["total_query_time_ms"])  # type: ignore
    slow = int(metrics_data["slow_queries"])  # type: ignore

    avg_time = total_time / total if total > 0 else 0
    slow_percentage = (slow / total * 100) if total > 0 else 0

    return {
        "total_queries": total,
        "slow_queries": slow,
        "avg_query_time_ms": round(avg_time, 2),
        "total_time_ms": round(total_time, 2),
        "slow_query_percentage": round(slow_percentage, 2),
        "slow_query_threshold_ms": SLOW_QUERY_THRESHOLD_MS,
        "slowest_queries": metrics_data["slowest_queries"],
    }


def reset_query_metrics() -> None:
    """Reset all query metrics (useful for testing or periodic resets)."""
    global metrics_data
    metrics_data = {
        "total_queries": 0,
        "slow_queries": 0,
        "total_query_time_ms": 0.0,
        "slowest_queries": [],
    }
    logger.info("Query metrics reset")


def track_operation_timing(operation_name: str) -> Callable:
    """
    Decorator to track general operation timing (not just queries).

    Args:
        operation_name: Name of the operation for logging

    Example:
        @track_operation_timing("embeddings_generation")
        async def generate_embeddings(texts: List[str]):
            # embedding operation
            return embeddings
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(f"Operation '{operation_name}' completed in {elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Operation '{operation_name}' failed after {elapsed_ms:.2f}ms: {str(e)}"
                )
                raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)  # type: ignore
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(f"Operation '{operation_name}' completed in {elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Operation '{operation_name}' failed after {elapsed_ms:.2f}ms: {str(e)}"
                )
                raise

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# Context manager for timing code blocks
class TimingContext:
    """
    Context manager for timing arbitrary code blocks.

    Example:
        with TimingContext("data_processing") as timer:
            # do work
            pass
        # Automatically logs timing
    """

    def __init__(self, operation_name: str, log_level: str = "INFO"):
        self.operation_name = operation_name
        self.log_level = log_level
        self.start_time: Optional[float] = None
        self.elapsed_ms: float = 0

    def __enter__(self) -> "TimingContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time:
            self.elapsed_ms = (time.time() - self.start_time) * 1000

            if exc_type:
                logger.error(
                    f"Operation '{self.operation_name}' failed after {self.elapsed_ms:.2f}ms"
                )
            else:
                log_func = getattr(logger, self.log_level.lower(), logger.info)
                log_func(f"Operation '{self.operation_name}' completed in {self.elapsed_ms:.2f}ms")
