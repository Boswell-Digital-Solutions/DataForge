"""
PHASE 2.2: Celery Retry + DLQ Tests

Comprehensive test suite for Dead Letter Queue, retry policies,
and Celery integration with exponential backoff.
"""
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock
from app.utils.dead_letter_queue import (
    get_dlq,
    reset_dlq,
    DeadLetterQueue,
    DLQItem,
    DLQItemStatus,
    RetryStrategy,
    DLQMetrics,
)
from app.utils.task_retry_policy import (
    get_retry_policy_registry,
    reset_retry_policy_registry,
    RetryPolicyRegistry,
    RetryPolicy,
    TaskCategory,
    get_policy_for_task,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def dlq():
    """Fresh DLQ instance."""
    reset_dlq()
    return get_dlq()


@pytest.fixture
def policy_registry():
    """Fresh policy registry."""
    reset_retry_policy_registry()
    return get_retry_policy_registry()


@pytest.fixture
def sample_dlq_item():
    """Sample DLQ item for testing."""
    return DLQItem(
        id="test-item-1",
        task_name="app.tasks.embeddings.generate_embeddings",
        task_id="task-123",
        args=[1, "test content"],
        kwargs={},
        exception="ConnectionError: API timeout",
        max_retries=3,
        retry_strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=60,
    )


# ============================================
# Test DLQItem
# ============================================

class TestDLQItem:
    """Test DLQ item functionality."""

    def test_dlq_item_creation(self, sample_dlq_item):
        """Test creating a DLQ item."""
        assert sample_dlq_item.id == "test-item-1"
        assert sample_dlq_item.task_name == "app.tasks.embeddings.generate_embeddings"
        assert sample_dlq_item.status == DLQItemStatus.FAILED
        assert sample_dlq_item.retry_count == 0

    def test_calculate_exponential_backoff(self, sample_dlq_item):
        """Test exponential backoff calculation."""
        # First retry: 60s
        next_retry_1 = sample_dlq_item.calculate_next_retry()
        assert next_retry_1 is not None
        assert 55 < (next_retry_1 - datetime.now(UTC)).total_seconds() < 65

        # Simulate retry
        sample_dlq_item.retry_count = 1
        next_retry_2 = sample_dlq_item.calculate_next_retry()
        assert next_retry_2 is not None
        delay_2 = (next_retry_2 - datetime.now(UTC)).total_seconds()
        assert 85 < delay_2 < 95  # ~90s (60 * 1.5)

    def test_mark_retrying(self, sample_dlq_item):
        """Test marking item as retrying."""
        sample_dlq_item.mark_retrying()
        
        assert sample_dlq_item.status == DLQItemStatus.RETRYING
        assert sample_dlq_item.retry_count == 1
        assert sample_dlq_item.last_retry_at is not None
        assert sample_dlq_item.next_retry_at is not None

    def test_mark_permanently_failed(self, sample_dlq_item):
        """Test marking item as permanently failed."""
        sample_dlq_item.mark_permanently_failed("Max retries exceeded")
        
        assert sample_dlq_item.status == DLQItemStatus.PERMANENTLY_FAILED
        assert sample_dlq_item.notes == "Max retries exceeded"
        assert len(sample_dlq_item.error_history) == 1

    def test_mark_resolved(self, sample_dlq_item):
        """Test marking item as resolved."""
        sample_dlq_item.mark_resolved("Fixed manually")
        
        assert sample_dlq_item.status == DLQItemStatus.RESOLVED
        assert sample_dlq_item.notes == "Fixed manually"

    def test_add_error_history(self, sample_dlq_item):
        """Test adding to error history."""
        sample_dlq_item.add_error_history("Timeout on retry 1")
        sample_dlq_item.add_error_history("Timeout on retry 2")
        
        assert len(sample_dlq_item.error_history) == 2
        assert "Timeout on retry 1" in sample_dlq_item.error_history[0]["error"]

    def test_dlq_item_to_dict(self, sample_dlq_item):
        """Test converting DLQ item to dictionary."""
        item_dict = sample_dlq_item.to_dict()
        
        assert item_dict["id"] == "test-item-1"
        assert item_dict["task_name"] == "app.tasks.embeddings.generate_embeddings"
        assert item_dict["status"] == "failed"


# ============================================
# Test DeadLetterQueue
# ============================================

class TestDeadLetterQueue:
    """Test Dead Letter Queue operations."""

    def test_add_item(self, dlq):
        """Test adding item to DLQ."""
        item = dlq.add_item(
            task_name="app.tasks.embeddings.generate_embeddings",
            task_id="task-123",
            exception="ConnectionError",
            args=[1, "content"],
            kwargs={},
        )
        
        assert item is not None
        assert dlq.get_item(item.id) == item
        assert len(dlq) == 1

    def test_get_item(self, dlq):
        """Test retrieving item from DLQ."""
        item = dlq.add_item(
            task_name="test-task",
            task_id="123",
            exception="Error",
            args=[],
            kwargs={},
        )
        
        retrieved = dlq.get_item(item.id)
        assert retrieved.id == item.id
        assert retrieved.task_name == "test-task"

    def test_get_nonexistent_item(self, dlq):
        """Test getting nonexistent item."""
        item = dlq.get_item("nonexistent")
        assert item is None

    def test_mark_retrying(self, dlq):
        """Test marking item for retry."""
        item = dlq.add_item(
            task_name="test-task",
            task_id="123",
            exception="Error",
            args=[],
            kwargs={},
        )
        
        success = dlq.mark_retrying(item.id)
        assert success is True
        
        updated_item = dlq.get_item(item.id)
        assert updated_item.status == DLQItemStatus.RETRYING
        assert updated_item.retry_count == 1

    def test_mark_permanently_failed(self, dlq):
        """Test marking item permanently failed."""
        item = dlq.add_item(
            task_name="test-task",
            task_id="123",
            exception="Error",
            args=[],
            kwargs={},
        )
        
        success = dlq.mark_permanently_failed(item.id, "Too many retries")
        assert success is True
        
        updated_item = dlq.get_item(item.id)
        assert updated_item.status == DLQItemStatus.PERMANENTLY_FAILED

    def test_mark_resolved(self, dlq):
        """Test marking item as resolved."""
        item = dlq.add_item(
            task_name="test-task",
            task_id="123",
            exception="Error",
            args=[],
            kwargs={},
        )
        
        success = dlq.mark_resolved(item.id, "Fixed with patch")
        assert success is True
        
        updated_item = dlq.get_item(item.id)
        assert updated_item.status == DLQItemStatus.RESOLVED

    def test_get_items_for_retry(self, dlq):
        """Test getting items ready for retry."""
        # Add items
        item1 = dlq.add_item(
            task_name="task1",
            task_id="123",
            exception="Error",
            args=[],
            kwargs={},
        )
        item2 = dlq.add_item(
            task_name="task2",
            task_id="124",
            exception="Error",
            args=[],
            kwargs={},
        )
        
        # Mark as retrying (sets next_retry_at to past)
        dlq.mark_retrying(item1.id)
        dlq.mark_retrying(item2.id)
        
        # Manually set next_retry_at to past
        item1_obj = dlq.get_item(item1.id)
        item1_obj.next_retry_at = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
        
        items = dlq.get_items_for_retry()
        assert len(items) >= 1
        assert item1.id in [i.id for i in items]

    def test_get_all_items_filtered(self, dlq):
        """Test retrieving items with filters."""
        dlq.add_item("task1", "123", "Error", [], {})
        dlq.add_item("task2", "124", "Error", [], {})
        dlq.add_item("task2", "125", "Error", [], {})
        
        items, total = dlq.get_all_items(task_name="task2")
        assert total == 2
        assert len(items) <= 2

    def test_dlq_metrics(self, dlq):
        """Test DLQ metrics tracking."""
        dlq.add_item("task1", "123", "Error", [], {})
        dlq.add_item("task1", "124", "Error", [], {})
        dlq.add_item("task2", "125", "Error", [], {})
        
        metrics = dlq.get_metrics()
        assert metrics.total_items == 3
        assert metrics.failed_items == 3

    def test_status_by_task(self, dlq):
        """Test status breakdown by task."""
        item1 = dlq.add_item("task1", "123", "Error", [], {})
        item2 = dlq.add_item("task1", "124", "Error", [], {})
        dlq.add_item("task2", "125", "Error", [], {})
        
        dlq.mark_retrying(item1.id)
        dlq.mark_permanently_failed(item2.id)
        
        status = dlq.get_status_by_task()
        assert "task1" in status
        assert "task2" in status
        assert status["task1"]["retrying"] == 1

    def test_cleanup_resolved_items(self, dlq):
        """Test cleaning up resolved items."""
        item1 = dlq.add_item("task1", "123", "Error", [], {})
        item2 = dlq.add_item("task2", "124", "Error", [], {})
        
        dlq.mark_resolved(item1.id)
        dlq.mark_resolved(item2.id)
        
        # Manually set old timestamp
        item1_obj = dlq.get_item(item1.id)
        item1_obj.created_at = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        
        count = dlq.cleanup_resolved_items(days_old=7)
        assert count >= 1


# ============================================
# Test RetryPolicy
# ============================================

class TestRetryPolicy:
    """Test retry policy configuration."""

    def test_policy_creation(self):
        """Test creating retry policy."""
        policy = RetryPolicy(
            max_retries=5,
            base_delay_seconds=30,
            backoff_multiplier=2.0,
        )
        
        assert policy.max_retries == 5
        assert policy.base_delay_seconds == 30
        assert policy.backoff_multiplier == 2.0

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(
            base_delay_seconds=60,
            backoff_multiplier=1.5,
            max_delay_seconds=3600,
            jitter_enabled=False,
        )
        
        delay_0 = policy.calculate_delay(0)
        delay_1 = policy.calculate_delay(1)
        delay_2 = policy.calculate_delay(2)
        
        assert delay_0 == 60
        assert delay_1 == 90  # 60 * 1.5
        assert delay_2 == 135  # 60 * 1.5^2

    def test_delay_max_cap(self):
        """Test max delay cap."""
        policy = RetryPolicy(
            base_delay_seconds=60,
            backoff_multiplier=2.0,
            max_delay_seconds=300,
            jitter_enabled=False,
        )
        
        # 60 * 2^5 = 1920, but capped at 300
        delay = policy.calculate_delay(5)
        assert delay == 300

    def test_jitter_enabled(self):
        """Test jitter adds variation."""
        policy = RetryPolicy(
            base_delay_seconds=100,
            backoff_multiplier=1.0,
            jitter_enabled=True,
        )
        
        delays = [policy.calculate_delay(1) for _ in range(10)]
        # Should have variation due to jitter
        assert len(set(delays)) > 1


# ============================================
# Test RetryPolicyRegistry
# ============================================

class TestRetryPolicyRegistry:
    """Test retry policy registry."""

    def test_registry_creation(self, policy_registry):
        """Test creating policy registry."""
        assert policy_registry is not None
        policies = policy_registry.get_all_policies()
        assert len(policies) > 0

    def test_get_policy_by_category(self, policy_registry):
        """Test getting policy by task category."""
        embedding_policy = policy_registry.get_policy("app.tasks.embeddings.generate_embeddings")
        search_policy = policy_registry.get_policy("app.tasks.search.batch_search")
        
        # Embedding tasks should have more retries
        assert embedding_policy.max_retries >= search_policy.max_retries

    def test_get_policy_with_inference(self, policy_registry):
        """Test policy inference from task name."""
        # Task not explicitly registered, but name contains 'embed'
        policy = policy_registry.get_policy("custom_embed_task")
        assert policy.max_retries > 0

    def test_register_custom_task(self, policy_registry):
        """Test registering custom task with policy."""
        custom_policy = RetryPolicy(max_retries=10)
        policy_registry.register_task(
            "custom.task",
            TaskCategory.EMBEDDINGS,
            custom_policy
        )
        
        policy = policy_registry.get_policy("custom.task")
        assert policy.max_retries == 10

    def test_task_category_registration(self, policy_registry):
        """Test registering task with category."""
        policy_registry.register_task(
            "app.custom.task",
            TaskCategory.INGESTION
        )
        
        category = policy_registry.get_task_category("app.custom.task")
        assert category == TaskCategory.INGESTION

    def test_get_all_policies_format(self, policy_registry):
        """Test getting all policies in dict format."""
        all_policies = policy_registry.get_all_policies()
        
        assert isinstance(all_policies, dict)
        for task_name, policy_dict in all_policies.items():
            assert "max_retries" in policy_dict
            assert "base_delay_seconds" in policy_dict


# ============================================
# Test Integration Functions
# ============================================

class TestRetryHelpers:
    """Test retry helper functions."""

    def test_get_policy_for_task(self, policy_registry):
        """Test getting policy for specific task."""
        policy = get_policy_for_task("app.tasks.embeddings.generate_embeddings")
        assert policy is not None
        assert policy.max_retries > 0

    def test_policy_for_unknown_task(self, policy_registry):
        """Test getting policy for unknown task falls back to default."""
        policy = get_policy_for_task("unknown.task.name")
        assert policy is not None
        assert policy.max_retries == 3  # Default value


# ============================================
# Test DLQMetrics
# ============================================

class TestDLQMetrics:
    """Test DLQ metrics."""

    def test_metrics_creation(self):
        """Test creating DLQ metrics."""
        metrics = DLQMetrics(
            total_items=10,
            failed_items=3,
            retrying_items=5,
        )
        
        assert metrics.total_items == 10
        assert metrics.failed_items == 3

    def test_metrics_to_dict(self):
        """Test converting metrics to dict."""
        metrics = DLQMetrics(total_items=10)
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["total_items"] == 10


# ============================================
# Integration Tests
# ============================================

class TestDLQIntegration:
    """Integration tests for DLQ system."""

    def test_complete_dlq_workflow(self, dlq):
        """Test complete DLQ workflow: add -> retry -> resolve."""
        # Add item
        item = dlq.add_item(
            task_name="test-task",
            task_id="123",
            exception="Error",
            args=[1, 2],
            kwargs={"key": "value"},
            max_retries=3,
        )
        
        assert dlq.get_metrics().total_items == 1
        
        # Mark for retry
        dlq.mark_retrying(item.id)
        assert dlq.get_item(item.id).retry_count == 1
        
        # Mark resolved
        dlq.mark_resolved(item.id, "Fixed")
        assert dlq.get_item(item.id).status == DLQItemStatus.RESOLVED

    def test_retry_with_policy(self, dlq, policy_registry):
        """Test DLQ retry with policy-based delays."""
        item = dlq.add_item(
            task_name="app.tasks.embeddings.generate_embeddings",
            task_id="123",
            exception="Error",
            args=[],
            kwargs={},
        )
        
        policy = get_policy_for_task("app.tasks.embeddings.generate_embeddings")
        
        dlq.mark_retrying(item.id)
        updated_item = dlq.get_item(item.id)
        
        # Verify next_retry_at is in future
        next_retry = datetime.fromisoformat(updated_item.next_retry_at)
        assert next_retry > datetime.now(UTC)
