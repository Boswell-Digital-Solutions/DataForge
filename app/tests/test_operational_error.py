"""
Tests for OperationalError.v1 — the BDS Useful Error Standard (ADR-006).

Hermetic: builds a throwaway FastAPI app and registers the real handlers, so no
database, Redis, or app lifespan is required.

Covers:
    - Explicit OperationalError renders the full envelope with its code/fields.
    - Existing bare HTTPException raises are wrapped into the same envelope.
    - Legacy `detail` field is preserved (backward compatibility).
    - Status -> code / retryable / severity derivation.
    - request_id is populated from the correlation middleware.
    - Retry-After (and other) headers survive.
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.errors import (
    SCHEMA_VERSION,
    SUBSYSTEM,
    ErrorSeverity,
    OperationalError,
    build_error_body,
    code_for_status,
    register_exception_handlers,
    retryable_for_status,
    severity_for_status,
)
from app.middleware.correlation import CorrelationIDMiddleware


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)
    register_exception_handlers(app)

    @app.get("/bare-404")
    def bare_404():
        raise HTTPException(status_code=404, detail="Run not found")

    @app.get("/bare-503")
    def bare_503():
        raise HTTPException(status_code=503, detail="Upstream down")

    @app.get("/explicit-409")
    def explicit_409():
        raise OperationalError(
            status_code=409,
            code="RUN_ALREADY_FINALIZED",
            safe_message="Run is finalized",
        )

    @app.get("/explicit-429")
    def explicit_429():
        raise OperationalError(
            status_code=429,
            code="RATE_LIMITED",
            safe_message="Slow down",
            retryable=True,
            severity=ErrorSeverity.WARNING,
            headers={"Retry-After": "30"},
        )

    @app.get("/explicit-refs")
    def explicit_refs():
        raise OperationalError(
            status_code=409,
            code="PROMOTION_BLOCKED",
            safe_message="Promotion blocked pending review",
            evidence_ref="sha256:abc",
            receipt_ref="receipt_123",
        )

    return TestClient(app, raise_server_exceptions=False)


# --- pure helpers ---------------------------------------------------------


def test_code_for_status_known_and_unknown():
    assert code_for_status(404) == "NOT_FOUND"
    assert code_for_status(409) == "CONFLICT"
    assert code_for_status(599) == "HTTP_599"


def test_retryable_only_for_transient_classes():
    assert retryable_for_status(503) is True
    assert retryable_for_status(429) is True
    assert retryable_for_status(404) is False
    assert retryable_for_status(400) is False


def test_severity_split_on_5xx():
    assert severity_for_status(500) == ErrorSeverity.ERROR
    assert severity_for_status(404) == ErrorSeverity.WARNING


def test_build_error_body_defaults_detail_to_safe_message():
    body = build_error_body(status_code=404, safe_message="missing")
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["subsystem"] == SUBSYSTEM
    assert body["code"] == "NOT_FOUND"
    assert body["detail"] == "missing"
    assert body["retryable"] is False
    assert "evidence_ref" not in body


# --- wrapped HTTPException ------------------------------------------------


def test_bare_http_exception_is_wrapped(client):
    r = client.get("/bare-404")
    assert r.status_code == 404
    body = r.json()
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["code"] == "NOT_FOUND"
    assert body["subsystem"] == SUBSYSTEM
    assert body["retryable"] is False
    assert body["severity"] == "warning"
    # Backward compatibility: legacy `detail` preserved.
    assert body["detail"] == "Run not found"
    assert body["safe_message"] == "Run not found"
    # request_id populated from correlation middleware.
    assert body["request_id"]
    assert body["request_id"] == r.headers["X-Correlation-ID"]


def test_bare_5xx_is_retryable_and_error_severity(client):
    r = client.get("/bare-503")
    assert r.status_code == 503
    body = r.json()
    assert body["code"] == "SERVICE_UNAVAILABLE"
    assert body["retryable"] is True
    assert body["severity"] == "error"


# --- explicit OperationalError -------------------------------------------


def test_explicit_operational_error_uses_supplied_code(client):
    r = client.get("/explicit-409")
    assert r.status_code == 409
    body = r.json()
    assert body["code"] == "RUN_ALREADY_FINALIZED"
    assert body["safe_message"] == "Run is finalized"
    assert body["detail"] == "Run is finalized"
    assert body["retryable"] is False  # 409 default


def test_explicit_error_preserves_headers_and_overrides(client):
    r = client.get("/explicit-429")
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "30"
    body = r.json()
    assert body["code"] == "RATE_LIMITED"
    assert body["retryable"] is True
    assert body["severity"] == "warning"


def test_explicit_error_emits_optional_refs(client):
    r = client.get("/explicit-refs")
    body = r.json()
    assert body["evidence_ref"] == "sha256:abc"
    assert body["receipt_ref"] == "receipt_123"
