"""
Celery-DLQ Integration

Connects Celery task failure signals to the Dead Letter Queue system.
Provides retry handlers with exponential backoff for failed tasks.
"""
import logging
from typing import Any, Dict, List
from celery.signals import task_failure, task_retry
from celery import Task

from app.utils.dead_letter_queue import get_dlq, RetryStrategy
from app.utils.task_retry_policy import get_policy_for_task

logger = logging.getLogger(__name__)


# ============================================
# Celery Signal Handlers
# ============================================

def setup_dlq_handlers(celery_app):
    """
    Register DLQ handlers with Celery signals.
    
    Call this in your FastAPI startup event or app initialization.
    
    Example:
        from app.tasks.celery_integration import setup_dlq_handlers
        from app.celery_app import get_celery_app
        
        @app.on_event("startup")
        async def startup():
            setup_dlq_handlers(get_celery_app())
    """
    
    @task_failure.connect
    def handle_task_failure(
        sender: Task,
        task_id: str,
        exception: Exception,
        args: tuple,
        kwargs: dict,
        traceback: Any,
        einfo: Any,
        **additional_kwargs
    ):
        """Handle task failure by adding to DLQ."""
        task_name = sender.name
        dlq = get_dlq()
        policy = get_policy_for_task(task_name)
        
        logger.error(
            f"Task {task_name} [{task_id}] failed with {exception.__class__.__name__}: {str(exception)}"
        )
        
        # Add to DLQ if configured
        if policy.send_to_dlq_on_failure:
            dlq.add_item(
                task_name=task_name,
                task_id=task_id,
                exception=f"{exception.__class__.__name__}: {str(exception)}",
                args=list(args),
                kwargs=kwargs,
                max_retries=policy.max_retries,
                retry_strategy=RetryStrategy.EXPONENTIAL,
                base_delay=policy.base_delay_seconds,
                priority=_get_task_priority(task_name)
            )
            logger.warning(f"Task {task_name} [{task_id}] added to DLQ")
    
    @task_retry.connect
    def handle_task_retry(
        sender: Task,
        task_id: str,
        reason: str,
        einfo: Any,
        **additional_kwargs
    ):
        """Handle task retry."""
        task_name = sender.name
        logger.warning(f"Task {task_name} [{task_id}] retrying: {reason}")


def _get_task_priority(task_name: str) -> int:
    """Determine task priority for DLQ."""
    if "embed" in task_name:
        return 1  # Highest priority
    elif "ingest" in task_name or "chunk" in task_name:
        return 2
    elif "search" in task_name:
        return 3
    elif "report" in task_name:
        return 5
    elif "maintain" in task_name or "cleanup" in task_name:
        return 10  # Lowest priority
    else:
        return 5  # Default


# ============================================
# Task Decorators
# ============================================

def dlq_task(
    bind: bool = True,
    auto_retry: bool = True,
    max_retries: int = 3,
    **task_kwargs
):
    """
    Decorator for tasks with DLQ support.
    
    Automatically handles retries with exponential backoff and adds
    permanently failed tasks to the DLQ.
    
    Args:
        bind: If True, passes task instance as first argument
        auto_retry: If True, applies retry logic based on policy
        max_retries: Maximum number of retries (overridable per task)
        **task_kwargs: Additional kwargs passed to @shared_task
    
    Example:
        @dlq_task(bind=True, max_retries=4)
        def my_task(self, document_id: int):
            try:
                # Task logic
                pass
            except Exception as exc:
                # Will be added to DLQ after max retries
                raise self.retry(exc=exc)
    """
    def decorator(func):
        from celery import shared_task
        from functools import wraps
        
        # Get policy for this task
        policy = get_policy_for_task(func.__module__ + "." + func.__name__)
        
        # Configure task kwargs
        celery_kwargs = {
            "bind": bind,
            "acks_late": True,
            "track_started": True,
            **task_kwargs
        }
        
        if auto_retry:
            celery_kwargs.update({
                "max_retries": policy.max_retries,
                "default_retry_delay": policy.base_delay_seconds,
                "autoretry_for": (Exception,),
            })
        
        # Apply shared_task decorator
        celery_decorated = shared_task(**celery_kwargs)(func)
        
        @wraps(celery_decorated)
        def wrapper(*args, **kwargs):
            return celery_decorated(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================
# Retry Helper
# ============================================

def calculate_task_retry_delay(
    task_name: str,
    retry_count: int,
    exception: Exception = None
) -> int:
    """
    Calculate retry delay for a task with exponential backoff.
    
    Args:
        task_name: Name of the task
        retry_count: Current retry attempt number (0-based)
        exception: Optional exception for logging
    
    Returns:
        Delay in seconds until next retry
    
    Example:
        try:
            # Task logic
            pass
        except Exception as exc:
            delay = calculate_task_retry_delay(task.name, task.request.retries, exc)
            raise task.retry(exc=exc, countdown=delay)
    """
    policy = get_policy_for_task(task_name)
    return policy.calculate_delay(retry_count)


# ============================================
# DLQ Monitoring Task
# ============================================

def create_dlq_monitoring_task(celery_app):
    """
    Create a periodic task to monitor and retry DLQ items.
    
    Add this to your celery beat schedule for automatic DLQ processing:
    
    Example in celery_app.py:
        from app.tasks.celery_integration import create_dlq_monitoring_task
        
        dlq_task = create_dlq_monitoring_task(celery_app)
        celery_app.conf.beat_schedule['dlq-monitoring'] = {
            'task': dlq_task,
            'schedule': 60.0,  # Every 60 seconds
            'options': {'queue': 'monitoring', 'priority': 10}
        }
    """
    
    @celery_app.task(name='app.tasks.maintenance.monitor_dlq')
    def monitor_dlq():
        """Monitor DLQ and process ready-for-retry items."""
        dlq = get_dlq()
        items_to_retry = dlq.get_items_for_retry()
        
        logger.info(f"DLQ Monitor: Found {len(items_to_retry)} items ready for retry")
        
        for item in items_to_retry[:10]:  # Process max 10 per cycle to avoid overload
            try:
                # Re-enqueue task with updated retry count
                task_func = _get_task_function(item.task_name)
                if task_func:
                    logger.info(f"Re-enqueueing task {item.task_name} [{item.id}]")
                    task_func.apply_async(
                        args=item.args,
                        kwargs=item.kwargs,
                        priority=item.priority,
                    )
                    dlq.mark_retrying(item.id)
                else:
                    logger.warning(f"Could not find task function: {item.task_name}")
                    dlq.mark_permanently_failed(
                        item.id,
                        reason="Task function not found"
                    )
            except Exception as exc:
                logger.error(f"Error re-enqueueing task {item.id}: {exc}")
                dlq.add_error_to_item(item.id, str(exc))
        
        # Clean up old resolved items
        dlq.cleanup_resolved_items(days_old=7)
        
        metrics = dlq.get_metrics()
        logger.info(
            f"DLQ Status: {metrics.total_items} total, "
            f"{metrics.permanently_failed_items} permanently failed"
        )
    
    return monitor_dlq


def _get_task_function(task_name: str):
    """Get Celery task function by name."""
    try:
        from celery import current_app
        return current_app.tasks.get(task_name)
    except Exception as e:
        logger.error(f"Error getting task function {task_name}: {e}")
        return None


# ============================================
# Configuration Helper
# ============================================

def configure_celery_for_dlq(celery_app, enable_monitoring: bool = True):
    """
    Full configuration helper to set up Celery with DLQ support.
    
    Call this in your app initialization:
    
    Example:
        from app.celery_app import get_celery_app
        from app.tasks.celery_integration import configure_celery_for_dlq
        
        @app.on_event("startup")
        async def startup():
            celery_app = get_celery_app()
            configure_celery_for_dlq(celery_app, enable_monitoring=True)
    
    Args:
        celery_app: Celery application instance
        enable_monitoring: If True, adds DLQ monitoring task to beat schedule
    """
    # Register signal handlers
    setup_dlq_handlers(celery_app)
    logger.info("DLQ signal handlers registered")
    
    # Add monitoring task if enabled
    if enable_monitoring:
        dlq_task = create_dlq_monitoring_task(celery_app)
        celery_app.conf.beat_schedule['dlq-monitoring'] = {
            'task': 'app.tasks.maintenance.monitor_dlq',
            'schedule': 60.0,  # Every 60 seconds
            'options': {'queue': 'maintenance', 'priority': 10}
        }
        logger.info("DLQ monitoring task added to beat schedule")
