"""
OperationalError.v1 — canonical structured error contract for DataForge.

Implements the BDS "Useful Error Standard" (BDS Formal Architecture
Investigation Report v1.0, Phase 2 / ADR-006) for the DataForge surface.

Before this module, DataForge emitted ``raise HTTPException(status_code, detail="...")``
free-text errors with no machine-readable code — the weakest error posture in the
ecosystem (Forge_Command already ships ``ErrorResponse {code, message, retriable}``).

This module provides three things:

1. A stable, machine-readable error envelope (schema ``operational_error.v1``) with
   the fields the report mandates: ``code``, ``safe_message``, ``subsystem``,
   ``request_id``, ``retryable``, ``severity``, and optional ``evidence_ref`` /
   ``receipt_ref``.
2. An :class:`OperationalError` exception so handlers can emit rich, explicit codes.
3. A global handler that wraps the *existing* ``HTTPException`` raises across all
   routers into the same envelope **without requiring each router to change**.

Backward compatibility: the legacy ``detail`` field is preserved in every envelope,
so existing clients and tests that read ``response.json()["detail"]`` keep working.
New consumers should branch on ``code`` / ``retryable`` rather than parsing
``safe_message``.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware.correlation import get_correlation_id

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "operational_error.v1"
SUBSYSTEM = "dataforge"


class ErrorSeverity(str, Enum):
    """Operational severity, independent of HTTP status."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Canonical, stable codes derived from HTTP status when a caller has not supplied
# an explicit one. New code should prefer raising OperationalError with a precise,
# domain-specific code (e.g. "RUN_ALREADY_FINALIZED") over relying on these.
_STATUS_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    410: "GONE",
    413: "PAYLOAD_TOO_LARGE",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "UPSTREAM_ERROR",
    503: "SERVICE_UNAVAILABLE",
    504: "UPSTREAM_TIMEOUT",
}

# Transient/transport classes are retryable by default; client errors are not.
_RETRYABLE_STATUS = {429, 502, 503, 504}


def code_for_status(status_code: int) -> str:
    """Return the canonical error code for an HTTP status."""
    return _STATUS_CODE_MAP.get(status_code, f"HTTP_{status_code}")


def retryable_for_status(status_code: int) -> bool:
    """Whether a status is retryable by default (transient transport classes only)."""
    return status_code in _RETRYABLE_STATUS


def severity_for_status(status_code: int) -> ErrorSeverity:
    """Default severity for a status: 5xx -> error, everything else -> warning."""
    return ErrorSeverity.ERROR if status_code >= 500 else ErrorSeverity.WARNING


def build_error_body(
    *,
    status_code: int,
    safe_message: str,
    code: Optional[str] = None,
    retryable: Optional[bool] = None,
    severity: Optional[ErrorSeverity] = None,
    request_id: Optional[str] = None,
    evidence_ref: Optional[str] = None,
    receipt_ref: Optional[str] = None,
    detail: Any = None,
) -> dict[str, Any]:
    """Build an ``operational_error.v1`` envelope.

    ``request_id`` defaults to the active correlation ID (set by
    :class:`CorrelationIDMiddleware`). ``detail`` is preserved for backward
    compatibility and falls back to ``safe_message`` when not provided.
    """
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "code": code or code_for_status(status_code),
        "safe_message": safe_message,
        "subsystem": SUBSYSTEM,
        "request_id": request_id if request_id is not None else get_correlation_id(),
        "retryable": retryable if retryable is not None else retryable_for_status(status_code),
        "severity": (severity or severity_for_status(status_code)).value,
    }
    if evidence_ref is not None:
        body["evidence_ref"] = evidence_ref
    if receipt_ref is not None:
        body["receipt_ref"] = receipt_ref
    # Legacy field, kept for backward compatibility with existing clients/tests.
    body["detail"] = detail if detail is not None else safe_message
    return body


class OperationalError(StarletteHTTPException):
    """A raisable structured error carrying OperationalError.v1 fields.

    Subclasses ``HTTPException`` so it flows through existing FastAPI machinery
    (and ``headers`` such as ``Retry-After`` still work), but is rendered by
    :func:`operational_error_handler` into the full envelope.

    Example::

        raise OperationalError(
            status_code=409,
            code="RUN_ALREADY_FINALIZED",
            safe_message="This run is finalized and cannot accept new findings.",
        )
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        safe_message: str,
        *,
        retryable: Optional[bool] = None,
        severity: Optional[ErrorSeverity] = None,
        evidence_ref: Optional[str] = None,
        receipt_ref: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=safe_message, headers=headers)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable
        self.severity = severity
        self.evidence_ref = evidence_ref
        self.receipt_ref = receipt_ref

    def to_body(self) -> dict[str, Any]:
        return build_error_body(
            status_code=self.status_code,
            safe_message=self.safe_message,
            code=self.code,
            retryable=self.retryable,
            severity=self.severity,
            evidence_ref=self.evidence_ref,
            receipt_ref=self.receipt_ref,
        )


async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """Render an explicit :class:`OperationalError` into its envelope."""
    return JSONResponse(status_code=exc.status_code, content=exc.to_body(), headers=exc.headers)


async def http_exception_envelope_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Wrap any ``HTTPException`` (the 150+ existing bare raises) into the envelope.

    Explicit :class:`OperationalError` instances carry richer fields, so delegate
    to their dedicated handler. Everything else derives a canonical code, severity,
    and retryability from the HTTP status while preserving the original ``detail``.
    """
    if isinstance(exc, OperationalError):
        return await operational_error_handler(request, exc)

    safe_message = (
        str(exc.detail) if exc.detail is not None else code_for_status(exc.status_code)
    )
    body = build_error_body(
        status_code=exc.status_code,
        safe_message=safe_message,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None)
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the OperationalError.v1 handlers on a FastAPI app.

    Registering for the base ``StarletteHTTPException`` overrides FastAPI's default
    handler and therefore also covers ``fastapi.HTTPException`` (a subclass).
    """
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_envelope_handler)
