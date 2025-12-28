"""
Correlation ID Middleware for DataForge

Enables request tracing across services by:
1. Accepting X-Correlation-ID header from incoming requests
2. Generating a UUID if not provided
3. Adding correlation_id to request.state for endpoint access
4. Echoing correlation_id back in response headers
5. Including correlation_id in all log entries
"""

import uuid
import time
import logging
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for thread-safe correlation ID access
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

logger = logging.getLogger(__name__)


def get_correlation_id() -> str | None:
    """Get current correlation ID from context"""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context"""
    correlation_id_var.set(correlation_id)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for request tracing.

    - Accepts X-Correlation-ID header from client
    - Generates UUID if not provided
    - Adds to request.state for handler access
    - Echoes back in response header
    - Includes in structured logs
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get correlation ID from headers (check both X-Correlation-ID and X-Request-ID)
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = request.headers.get("X-Request-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state for access in endpoints
        request.state.correlation_id = correlation_id
        request.state.request_id = correlation_id  # Alias for compatibility

        # Set in context for thread-safe access
        set_correlation_id(correlation_id)

        # Log request received
        start_time = time.time()
        logger.info(
            "request_received",
            extra={
                "correlation_id": correlation_id,
                "service": "dataforge",
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            },
        )

        try:
            response = await call_next(request)

            # Add correlation ID to response headers (both formats for compatibility)
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = correlation_id

            # Log request completed
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "request_completed",
                extra={
                    "correlation_id": correlation_id,
                    "service": "dataforge",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return response

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "request_failed",
                extra={
                    "correlation_id": correlation_id,
                    "service": "dataforge",
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise
