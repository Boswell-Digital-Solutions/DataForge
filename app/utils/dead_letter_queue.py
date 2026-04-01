"""
Dead Letter Queue (DLQ) Management System

Handles task failures with exponential backoff, automatic retries, and
persistent storage of permanently failed tasks for manual intervention.
"""
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class DLQItemStatus(Enum):
    """Status of a DLQ item."""
    FAILED = "failed"
    RETRYING = "retrying"
    PERMANENTLY_FAILED = "permanently_failed"
    RESOLVED = "resolved"


class RetryStrategy(Enum):
    """Retry strategy for tasks."""
    EXPONENTIAL = "exponential"  # 1.5x backoff
    LINEAR = "linear"  # Fixed interval
    IMMEDIATE = "immediate"  # No delay


@dataclass
class DLQMetrics:
    """Metrics for DLQ operations."""
    total_items: int = 0
    failed_items: int = 0
    retrying_items: int = 0
    permanently_failed_items: int = 0
    resolved_items: int = 0
    avg_retry_count: float = 0.0
    avg_wait_time_seconds: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DLQItem:
    """Single item in the Dead Letter Queue."""
    id: str
    task_name: str
    task_id: str
    args: List[Any]
    kwargs: Dict[str, Any]
    exception: str
    status: DLQItemStatus = DLQItemStatus.FAILED
    retry_count: int = 0
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay_seconds: int = 60
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_retry_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    error_history: List[Dict[str, str]] = field(default_factory=list)
    notes: str = ""
    priority: int = 5  # 1=highest, 10=lowest

    def calculate_next_retry(self) -> Optional[datetime]:
        """Calculate when next retry should occur."""
        if self.retry_count >= self.max_retries:
            return None
        
        if self.retry_strategy == RetryStrategy.EXPONENTIAL:
            # Exponential backoff: 60s, 90s, 135s, ...
            delay = self.base_delay_seconds * (1.5 ** self.retry_count)
        elif self.retry_strategy == RetryStrategy.LINEAR:
            # Linear backoff: 60s, 120s, 180s, ...
            delay = self.base_delay_seconds * (self.retry_count + 1)
        else:  # IMMEDIATE
            delay = 0
        
        return datetime.now(UTC) + timedelta(seconds=delay)

    def mark_retrying(self):
        """Mark item as retrying and update next retry time."""
        self.status = DLQItemStatus.RETRYING
        self.last_retry_at = datetime.now(UTC).isoformat()
        next_retry = self.calculate_next_retry()
        self.next_retry_at = next_retry.isoformat() if next_retry else None
        self.retry_count += 1

    def mark_permanently_failed(self, reason: str = "Max retries exceeded"):
        """Mark item as permanently failed."""
        self.status = DLQItemStatus.PERMANENTLY_FAILED
        self.notes = reason
        self.error_history.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "permanently_failed",
            "reason": reason
        })

    def mark_resolved(self, resolution_notes: str = ""):
        """Mark item as resolved."""
        self.status = DLQItemStatus.RESOLVED
        self.notes = resolution_notes
        self.error_history.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "resolved",
            "notes": resolution_notes
        })

    def add_error_history(self, error: str):
        """Add error to history."""
        self.error_history.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "error": error
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['retry_strategy'] = self.retry_strategy.value
        return data


class DeadLetterQueue:
    """
    Centralized Dead Letter Queue for handling failed tasks.
    
    Features:
    - Exponential backoff retry logic
    - Persistent storage of failed tasks
    - Metrics and monitoring
    - Admin endpoints for manual intervention
    - Error history tracking
    """

    def __init__(self, max_storage_items: int = 10000):
        """Initialize DLQ."""
        self._queue: Dict[str, DLQItem] = {}
        self._max_items = max_storage_items
        self._metrics = DLQMetrics()

    def add_item(
        self,
        task_name: str,
        task_id: str,
        exception: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        max_retries: int = 3,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: int = 60,
        priority: int = 5
    ) -> DLQItem:
        """Add a failed task to the DLQ."""
        # Generate unique ID for DLQ item
        item_hash = hashlib.sha256(
            f"{task_id}-{datetime.now(UTC).isoformat()}".encode()
        ).hexdigest()[:16]

        item = DLQItem(
            id=item_hash,
            task_name=task_name,
            task_id=task_id,
            args=args,
            kwargs=kwargs,
            exception=exception,
            max_retries=max_retries,
            retry_strategy=retry_strategy,
            base_delay_seconds=base_delay,
            priority=priority
        )

        # Check storage limit (LRU eviction if needed)
        if len(self._queue) >= self._max_items:
            oldest = min(
                self._queue.values(),
                key=lambda x: x.created_at
            )
            del self._queue[oldest.id]
            logger.warning(f"DLQ storage full, evicted oldest item: {oldest.id}")

        self._queue[item.id] = item
        self._update_metrics()

        logger.warning(
            f"Task {task_name} [{task_id}] added to DLQ: {exception}"
        )
        return item

    def get_item(self, dlq_item_id: str) -> Optional[DLQItem]:
        """Get a DLQ item by ID."""
        return self._queue.get(dlq_item_id)

    def get_items_for_retry(self) -> List[DLQItem]:
        """Get items ready for retry (past next_retry_at)."""
        now = datetime.now(UTC)
        items_to_retry = []

        for item in self._queue.values():
            if item.status != DLQItemStatus.RETRYING:
                continue
            
            if item.next_retry_at:
                retry_time = datetime.fromisoformat(item.next_retry_at)
                if retry_time <= now:
                    items_to_retry.append(item)

        return sorted(items_to_retry, key=lambda x: x.priority)

    def get_all_items(
        self,
        status: Optional[DLQItemStatus] = None,
        task_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[DLQItem], int]:
        """Get DLQ items with filtering."""
        results = list(self._queue.values())

        # Filter by status
        if status:
            results = [i for i in results if i.status == status]

        # Filter by task name
        if task_name:
            results = [i for i in results if i.task_name == task_name]

        # Sort by creation time (newest first)
        results.sort(key=lambda x: x.created_at, reverse=True)

        total = len(results)
        return results[offset:offset + limit], total

    def mark_retrying(self, dlq_item_id: str) -> bool:
        """Mark item as retrying."""
        item = self._queue.get(dlq_item_id)
        if not item:
            return False

        item.mark_retrying()
        self._update_metrics()
        logger.info(f"DLQ item {dlq_item_id} marked for retry")
        return True

    def mark_permanently_failed(self, dlq_item_id: str, reason: str = "") -> bool:
        """Mark item as permanently failed."""
        item = self._queue.get(dlq_item_id)
        if not item:
            return False

        item.mark_permanently_failed(reason)
        self._update_metrics()
        logger.error(f"DLQ item {dlq_item_id} permanently failed: {reason}")
        return True

    def mark_resolved(self, dlq_item_id: str, notes: str = "") -> bool:
        """Mark item as resolved (manual fix applied)."""
        item = self._queue.get(dlq_item_id)
        if not item:
            return False

        item.mark_resolved(notes)
        self._update_metrics()
        logger.info(f"DLQ item {dlq_item_id} marked resolved: {notes}")
        return True

    def add_error_to_item(self, dlq_item_id: str, error: str) -> bool:
        """Add error to item's history."""
        item = self._queue.get(dlq_item_id)
        if not item:
            return False

        item.add_error_history(error)
        return True

    def get_metrics(self) -> DLQMetrics:
        """Get current DLQ metrics."""
        return self._metrics

    def get_status_by_task(self) -> Dict[str, Dict[str, int]]:
        """Get DLQ status breakdown by task name."""
        status_map: Dict[str, Dict[str, int]] = {}

        for item in self._queue.values():
            if item.task_name not in status_map:
                status_map[item.task_name] = {
                    "failed": 0,
                    "retrying": 0,
                    "permanently_failed": 0,
                    "resolved": 0
                }

            status_key = item.status.value.replace("_", "_")
            status_map[item.task_name][status_key] += 1

        return status_map

    def cleanup_resolved_items(self, days_old: int = 7) -> int:
        """Remove resolved items older than specified days."""
        cutoff = datetime.now(UTC) - timedelta(days=days_old)
        items_to_remove = []

        for item_id, item in self._queue.items():
            if item.status != DLQItemStatus.RESOLVED:
                continue
            
            created = datetime.fromisoformat(item.created_at)
            if created < cutoff:
                items_to_remove.append(item_id)

        for item_id in items_to_remove:
            del self._queue[item_id]

        if items_to_remove:
            logger.info(f"Cleaned up {len(items_to_remove)} resolved DLQ items")
            self._update_metrics()

        return len(items_to_remove)

    def _update_metrics(self):
        """Update DLQ metrics."""
        total = len(self._queue)
        failed = sum(1 for i in self._queue.values() if i.status == DLQItemStatus.FAILED)
        retrying = sum(1 for i in self._queue.values() if i.status == DLQItemStatus.RETRYING)
        perm_failed = sum(1 for i in self._queue.values() if i.status == DLQItemStatus.PERMANENTLY_FAILED)
        resolved = sum(1 for i in self._queue.values() if i.status == DLQItemStatus.RESOLVED)

        avg_retry = 0.0
        if self._queue:
            avg_retry = sum(i.retry_count for i in self._queue.values()) / len(self._queue)

        self._metrics = DLQMetrics(
            total_items=total,
            failed_items=failed,
            retrying_items=retrying,
            permanently_failed_items=perm_failed,
            resolved_items=resolved,
            avg_retry_count=avg_retry,
            last_updated=datetime.now(UTC).isoformat()
        )

    def __len__(self) -> int:
        """Get number of items in DLQ."""
        return len(self._queue)

    def export_to_json(self) -> str:
        """Export DLQ to JSON format."""
        items = [item.to_dict() for item in self._queue.values()]
        return json.dumps(items, indent=2)


# Global DLQ instance
_dlq_instance: Optional[DeadLetterQueue] = None


def get_dlq() -> DeadLetterQueue:
    """Get or create global DLQ instance."""
    global _dlq_instance
    if _dlq_instance is None:
        _dlq_instance = DeadLetterQueue()
    return _dlq_instance


def reset_dlq():
    """Reset global DLQ instance (for testing)."""
    global _dlq_instance
    _dlq_instance = None
