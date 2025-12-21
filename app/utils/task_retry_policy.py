"""
Task Retry Policy Configuration

Defines per-task retry behavior with exponential backoff, max retries,
and DLQ integration for permanently failed tasks.
"""
import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """Task categories for retry policies."""
    EMBEDDINGS = "embeddings"
    SEARCH = "search"
    INGESTION = "ingestion"
    MAINTENANCE = "maintenance"
    REPORTING = "reporting"
    DEFAULT = "default"


@dataclass
class RetryPolicy:
    """Retry policy for a task or task category."""
    max_retries: int = 3
    base_delay_seconds: int = 60
    backoff_multiplier: float = 1.5
    max_delay_seconds: int = 3600  # Cap at 1 hour
    send_to_dlq_on_failure: bool = True
    task_timeout_seconds: Optional[int] = None
    jitter_enabled: bool = True  # Add random jitter to prevent thundering herd

    def calculate_delay(self, retry_count: int) -> int:
        """Calculate retry delay with exponential backoff."""
        if retry_count == 0:
            return self.base_delay_seconds
        
        # Exponential: base * (multiplier ^ retry_count)
        delay = int(self.base_delay_seconds * (self.backoff_multiplier ** retry_count))
        
        # Cap at max delay
        delay = min(delay, self.max_delay_seconds)
        
        # Add jitter to prevent thundering herd
        if self.jitter_enabled:
            import random
            jitter = random.randint(0, int(delay * 0.1))  # ±10% jitter
            delay = delay + jitter
        
        return delay

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_retries": self.max_retries,
            "base_delay_seconds": self.base_delay_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "max_delay_seconds": self.max_delay_seconds,
            "send_to_dlq_on_failure": self.send_to_dlq_on_failure,
            "task_timeout_seconds": self.task_timeout_seconds,
            "jitter_enabled": self.jitter_enabled,
        }


class RetryPolicyRegistry:
    """
    Registry for task retry policies.
    
    Maps task names or categories to specific retry behaviors.
    Supports fallback to default policy for unmapped tasks.
    """

    def __init__(self):
        """Initialize policy registry."""
        self._policies: Dict[str, RetryPolicy] = {}
        self._task_to_category: Dict[str, TaskCategory] = {}
        
        # Register default policies
        self._register_defaults()

    def _register_defaults(self):
        """Register default retry policies for each category."""
        
        # Embedding tasks: High priority, may need retries due to API limits
        self._policies[TaskCategory.EMBEDDINGS.value] = RetryPolicy(
            max_retries=4,  # More retries for API rate limiting
            base_delay_seconds=60,
            backoff_multiplier=1.5,
            max_delay_seconds=1800,  # 30 minutes
            task_timeout_seconds=300,  # 5 minute timeout
        )

        # Search tasks: Medium priority
        self._policies[TaskCategory.SEARCH.value] = RetryPolicy(
            max_retries=3,
            base_delay_seconds=30,
            backoff_multiplier=2.0,
            max_delay_seconds=600,  # 10 minutes
            task_timeout_seconds=60,
        )

        # Ingestion tasks: High priority, important for data flow
        self._policies[TaskCategory.INGESTION.value] = RetryPolicy(
            max_retries=5,
            base_delay_seconds=45,
            backoff_multiplier=1.5,
            max_delay_seconds=2400,  # 40 minutes
            task_timeout_seconds=600,  # 10 minute timeout
        )

        # Maintenance tasks: Low priority
        self._policies[TaskCategory.MAINTENANCE.value] = RetryPolicy(
            max_retries=2,
            base_delay_seconds=120,
            backoff_multiplier=2.0,
            max_delay_seconds=900,  # 15 minutes
            task_timeout_seconds=300,
        )

        # Reporting tasks: Low priority
        self._policies[TaskCategory.REPORTING.value] = RetryPolicy(
            max_retries=2,
            base_delay_seconds=60,
            backoff_multiplier=2.0,
            max_delay_seconds=600,
            task_timeout_seconds=180,
        )

        # Default fallback policy
        self._policies[TaskCategory.DEFAULT.value] = RetryPolicy(
            max_retries=3,
            base_delay_seconds=60,
            backoff_multiplier=1.5,
            max_delay_seconds=3600,
        )

    def register_task(
        self,
        task_name: str,
        category: TaskCategory,
        policy: Optional[RetryPolicy] = None
    ):
        """Register a task with a category and optional custom policy."""
        self._task_to_category[task_name] = category
        
        if policy:
            self._policies[task_name] = policy
            logger.info(f"Registered custom policy for task: {task_name}")
        else:
            logger.info(f"Registered task {task_name} with category {category.value}")

    def get_policy(self, task_name: str) -> RetryPolicy:
        """Get retry policy for a task."""
        
        # Check if exact task name is registered
        if task_name in self._policies:
            return self._policies[task_name]

        # Check if task has a category
        if task_name in self._task_to_category:
            category = self._task_to_category[task_name]
            if category.value in self._policies:
                return self._policies[category.value]

        # Try to infer category from task name pattern
        if "embed" in task_name:
            return self._policies[TaskCategory.EMBEDDINGS.value]
        elif "search" in task_name:
            return self._policies[TaskCategory.SEARCH.value]
        elif "ingest" in task_name or "chunk" in task_name:
            return self._policies[TaskCategory.INGESTION.value]
        elif "maintain" in task_name or "cleanup" in task_name:
            return self._policies[TaskCategory.MAINTENANCE.value]
        elif "report" in task_name:
            return self._policies[TaskCategory.REPORTING.value]

        # Fall back to default
        return self._policies[TaskCategory.DEFAULT.value]

    def set_policy(self, task_name_or_category: str, policy: RetryPolicy):
        """Set a custom retry policy."""
        self._policies[task_name_or_category] = policy
        logger.info(f"Updated policy for: {task_name_or_category}")

    def get_all_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered policies."""
        return {
            name: policy.to_dict()
            for name, policy in self._policies.items()
        }

    def get_task_category(self, task_name: str) -> TaskCategory:
        """Get category for a task."""
        return self._task_to_category.get(
            task_name,
            TaskCategory.DEFAULT
        )


# Global policy registry
_registry: Optional[RetryPolicyRegistry] = None


def get_retry_policy_registry() -> RetryPolicyRegistry:
    """Get or create global retry policy registry."""
    global _registry
    if _registry is None:
        _registry = RetryPolicyRegistry()
        _register_standard_tasks()
    return _registry


def _register_standard_tasks():
    """Register standard DataForge tasks with their categories."""
    registry = _registry
    
    # Embedding tasks
    for task_name in [
        "app.tasks.embeddings.generate_embeddings",
        "app.tasks.embeddings.reindex_documents",
        "app.tasks.embeddings.reindex_stale_documents",
    ]:
        registry.register_task(task_name, TaskCategory.EMBEDDINGS)

    # Search tasks
    for task_name in [
        "app.tasks.search.batch_search",
        "app.tasks.search.semantic_search_async",
        "app.tasks.search.search_with_filters",
    ]:
        registry.register_task(task_name, TaskCategory.SEARCH)

    # Maintenance tasks
    for task_name in [
        "app.tasks.maintenance.cleanup_old_cache",
        "app.tasks.maintenance.health_check",
        "app.tasks.maintenance.cleanup_old_results",
        "app.tasks.maintenance.purge_failed_tasks",
    ]:
        registry.register_task(task_name, TaskCategory.MAINTENANCE)

    # Reporting tasks
    for task_name in [
        "app.tasks.reporting.generate_daily_statistics",
        "app.tasks.reporting.generate_performance_report",
        "app.tasks.reporting.generate_user_activity_report",
    ]:
        registry.register_task(task_name, TaskCategory.REPORTING)


def get_policy_for_task(task_name: str) -> RetryPolicy:
    """Convenience function to get policy for a specific task."""
    registry = get_retry_policy_registry()
    return registry.get_policy(task_name)


def reset_retry_policy_registry():
    """Reset global registry (for testing)."""
    global _registry
    _registry = None
