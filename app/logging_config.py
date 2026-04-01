"""
Logging Configuration Module

Provides centralized, production-grade logging with structured logs,
audit trails, security event logging, and log rotation.
"""

import logging
import logging.handlers
import json
from datetime import datetime, UTC
from typing import Optional
import os
import sys
from functools import wraps


class StructuredJSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add optional fields if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'security_event'):
            log_data['security_event'] = record.security_event
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to all log records."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__()
        self.correlation_id = correlation_id
    
    def filter(self, record):
        """Add correlation ID to log record."""
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = self.correlation_id
        return True


class SecurityEventFilter(logging.Filter):
    """Filter to identify and flag security-related events."""
    
    SECURITY_KEYWORDS = [
        'auth', 'authentication', 'authorization', 'permission',
        'login', 'logout', 'token', 'session', 'credential',
        'encrypt', 'decrypt', 'password', 'secret', 'key',
        'access', 'denied', 'forbidden', 'unauthorized',
        'breach', 'attack', 'injection', 'xss', 'csrf',
        'sql', 'privilege', 'escalation', 'vulnerability',
        'suspicious', 'anomaly', 'threat', 'alert'
    ]
    
    def filter(self, record):
        """Mark security events in log record."""
        message = record.getMessage().lower()
        
        is_security_event = any(
            keyword in message 
            for keyword in self.SECURITY_KEYWORDS
        ) or record.levelname in ['WARNING', 'ERROR', 'CRITICAL']
        
        record.security_event = is_security_event
        return True


def configure_logging(
    log_level: str = "INFO",
    log_file: str = "logs/dataforge.log",
    security_log_file: str = "logs/security.log",
    access_log_file: str = "logs/access.log",
    json_format: bool = True,
    correlation_id: Optional[str] = None
):
    """
    Configure comprehensive logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to main application log file
        security_log_file: Path to security events log file
        access_log_file: Path to access/request log file
        json_format: Whether to use JSON structured logging
        correlation_id: Optional correlation ID for tracing
    """
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Get numeric log level
    numeric_log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    if json_format:
        json_formatter = StructuredJSONFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
        console_formatter = json_formatter
    else:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        console_formatter = logging.Formatter(format_string)
        json_formatter = logging.Formatter(format_string)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add correlation ID and security event filters
    correlation_filter = CorrelationIdFilter(correlation_id)
    security_filter = SecurityEventFilter()
    root_logger.addFilter(correlation_filter)
    root_logger.addFilter(security_filter)
    
    # Console handler for INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Main application file handler with rotation
    try:
        main_file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,  # Keep 10 backup files (100 MB total)
            encoding='utf-8'
        )
        main_file_handler.setLevel(numeric_log_level)
        main_file_handler.setFormatter(json_formatter if json_format else console_formatter)
        main_file_handler.addFilter(correlation_filter)
        root_logger.addHandler(main_file_handler)
    except (IOError, OSError) as e:
        root_logger.warning(f"Could not create main log file: {e}")
    
    # Security-focused file handler
    try:
        security_handler = logging.handlers.RotatingFileHandler(
            security_log_file,
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=30,  # Keep 30 backup files (1.5 GB total)
            encoding='utf-8'
        )
        security_handler.setLevel(logging.WARNING)
        security_handler.setFormatter(json_formatter if json_format else console_formatter)
        security_handler.addFilter(correlation_filter)
        security_handler.addFilter(security_filter)
        
        # Only log security events
        def security_filter_handler(record):
            return getattr(record, 'security_event', False)
        
        security_handler.addFilter(logging.Filter())
        security_handler.filter = security_filter_handler
        
        root_logger.addHandler(security_handler)
    except (IOError, OSError) as e:
        root_logger.warning(f"Could not create security log file: {e}")
    
    # Access log handler (for API requests)
    try:
        access_handler = logging.handlers.RotatingFileHandler(
            access_log_file,
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=20,  # Keep 20 backup files (1 GB total)
            encoding='utf-8'
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(json_formatter if json_format else console_formatter)
        access_handler.addFilter(correlation_filter)
        
        # Get or create access logger
        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addHandler(access_handler)
        access_logger.setLevel(logging.INFO)
    except (IOError, OSError) as e:
        root_logger.warning(f"Could not create access log file: {e}")
    
    return root_logger


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    additional_data: Optional[dict] = None
):
    """
    Log a security event with structured data.
    
    Args:
        logger: Logger instance
        event_type: Type of security event (e.g., 'AUTHENTICATION_FAILURE', 'UNAUTHORIZED_ACCESS')
        description: Human-readable description
        user_id: User ID associated with event
        correlation_id: Correlation ID for tracing
        additional_data: Additional structured data to log
    """
    
    extra = {
        'security_event': True,
        'event_type': event_type,
    }
    
    if user_id:
        extra['user_id'] = user_id
    
    if correlation_id:
        extra['correlation_id'] = correlation_id
    
    if additional_data:
        extra.update(additional_data)
    
    logger.warning(
        f"SECURITY EVENT [{event_type}]: {description}",
        extra=extra
    )


def log_audit_event(
    logger: logging.Logger,
    action: str,
    resource: str,
    user_id: Optional[str] = None,
    result: str = "SUCCESS",
    correlation_id: Optional[str] = None,
    additional_data: Optional[dict] = None
):
    """
    Log an audit event for compliance and accountability.
    
    Args:
        logger: Logger instance
        action: Action performed (e.g., 'CREATE', 'UPDATE', 'DELETE')
        resource: Resource affected (e.g., 'user', 'project', 'api_key')
        user_id: User ID performing the action
        result: Result of the action (SUCCESS, FAILURE, DENIED)
        correlation_id: Correlation ID for tracing
        additional_data: Additional structured data
    """
    
    extra = {
        'audit_event': True,
        'action': action,
        'resource': resource,
        'result': result,
    }
    
    if user_id:
        extra['user_id'] = user_id
    
    if correlation_id:
        extra['correlation_id'] = correlation_id
    
    if additional_data:
        extra.update(additional_data)
    
    level = logging.INFO if result == "SUCCESS" else logging.WARNING
    
    logger.log(
        level,
        f"AUDIT [{action}] {resource}: {result}",
        extra=extra
    )


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    response_size: Optional[int] = None
):
    """
    Log API request/response information.
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP response status code
        duration_ms: Request duration in milliseconds
        user_id: User ID (if authenticated)
        correlation_id: Correlation ID for tracing
        response_size: Response size in bytes
    """
    
    extra = {
        'method': method,
        'path': path,
        'status_code': status_code,
        'duration_ms': duration_ms,
    }
    
    if user_id:
        extra['user_id'] = user_id
    
    if correlation_id:
        extra['correlation_id'] = correlation_id
    
    if response_size:
        extra['response_size'] = response_size
    
    # Determine log level based on status code
    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    
    logger.log(
        level,
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra=extra
    )


class LoggingContextManager:
    """Context manager for adding logging context (e.g., user_id, correlation_id)."""
    
    _context = {}
    
    @classmethod
    def set(cls, key: str, value):
        """Set a logging context value."""
        cls._context[key] = value
    
    @classmethod
    def get(cls, key: str, default=None):
        """Get a logging context value."""
        return cls._context.get(key, default)
    
    @classmethod
    def clear(cls):
        """Clear all logging context."""
        cls._context.clear()
    
    @classmethod
    def get_all(cls):
        """Get all logging context."""
        return cls._context.copy()


# Default logger instance
_default_logger = None


def get_logger(name: str = "dataforge") -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically module name)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def initialize_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    json_format: bool = True,
    correlation_id: Optional[str] = None
) -> logging.Logger:
    """
    Initialize application logging (call once at startup).
    
    Args:
        log_level: Logging level
        log_dir: Directory for log files
        json_format: Use JSON structured logging
        correlation_id: Optional correlation ID
        
    Returns:
        Root logger instance
    """
    global _default_logger
    
    log_file = os.path.join(log_dir, "dataforge.log")
    security_log_file = os.path.join(log_dir, "security.log")
    access_log_file = os.path.join(log_dir, "access.log")
    
    _default_logger = configure_logging(
        log_level=log_level,
        log_file=log_file,
        security_log_file=security_log_file,
        access_log_file=access_log_file,
        json_format=json_format,
        correlation_id=correlation_id
    )
    
    return _default_logger
