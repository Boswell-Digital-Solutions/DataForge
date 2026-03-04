"""ASGI request timeout middleware for protecting the worker event loop."""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RequestTimeoutMiddleware:
    """Return HTTP 504 when a request exceeds the configured timeout."""

    def __init__(self, app, timeout_seconds: float = 30.0):
        self.app = app
        self.timeout_seconds = timeout_seconds

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or self.timeout_seconds <= 0:
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        start = time.perf_counter()
        task = asyncio.create_task(self.app(scope, receive, send_wrapper))
        try:
            done, pending = await asyncio.wait({task}, timeout=self.timeout_seconds)
            if task in done:
                await task
                return

            for pending_task in pending:
                pending_task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

            duration_ms = int((time.perf_counter() - start) * 1000)
            headers = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            correlation_id = headers.get("x-correlation-id") or headers.get("x-request-id")

            logger.error(
                "request_timeout",
                extra={
                    "correlation_id": correlation_id,
                    "service": "dataforge",
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "duration_ms": duration_ms,
                    "timeout_seconds": self.timeout_seconds,
                },
            )

            if response_started:
                return

            response = JSONResponse(
                status_code=504,
                content={
                    "detail": {
                        "error": "REQUEST_TIMEOUT",
                        "message": f"Request exceeded {self.timeout_seconds:.1f}s timeout",
                        "path": scope.get("path"),
                    }
                },
            )
            if correlation_id:
                response.headers["X-Correlation-ID"] = correlation_id
                response.headers["X-Request-ID"] = correlation_id
            await response(scope, receive, send)
        except Exception:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            raise
