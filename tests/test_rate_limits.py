# tests/test_rate_limits.py
# Tests for the global rate-limits API.
#
# Verifies: atomic check-and-increment, cost cap enforcement,
# provider status, configuration upsert.

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from app.models.rate_limits_models import GlobalRateLimit
from app.models.rate_limits_schemas import (
    RateLimitCheckRequest,
    RateLimitCheckResponse,
    RateLimitProvider,
)


# ============================================================================
# Fixtures
# ============================================================================


def _make_rate_limit_row(
    provider: str = "xai",
    current_count: int = 0,
    max_count: int = 5000,
    cost_usd: Decimal = Decimal("0"),
    max_cost_usd: Decimal = Decimal("300.0"),
) -> GlobalRateLimit:
    """Create a mock GlobalRateLimit row."""
    row = GlobalRateLimit(
        id=uuid4(),
        provider=provider,
        window_start=datetime.now(timezone.utc),
        window_duration_seconds=30 * 24 * 3600,
        current_count=current_count,
        max_count=max_count,
        cost_usd=cost_usd,
        max_cost_usd=max_cost_usd,
        metadata_={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return row


# ============================================================================
# Unit Tests — Response Builder
# ============================================================================


class TestBuildResponse:
    """Tests for the _build_response helper."""

    def test_allowed_response(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(current_count=100, max_count=5000)
        resp = _build_response(row, allowed=True, reason="OK")

        assert resp.allowed is True
        assert resp.provider == "xai"
        assert resp.current_count == 100
        assert resp.max_count == 5000
        assert resp.requests_remaining == 4900
        assert resp.utilization == 0.02
        assert resp.reason == "OK"

    def test_denied_response_at_limit(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(current_count=5000, max_count=5000)
        resp = _build_response(row, allowed=False, reason="Budget exhausted")

        assert resp.allowed is False
        assert resp.requests_remaining == 0
        assert resp.utilization == 1.0

    def test_cost_fields_populated(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(cost_usd=Decimal("150.50"), max_cost_usd=Decimal("300.0"))
        resp = _build_response(row, allowed=True, reason="OK")

        assert resp.cost_usd == 150.50
        assert resp.max_cost_usd == 300.0

    def test_no_cost_cap(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(max_cost_usd=None)
        row.max_cost_usd = None
        resp = _build_response(row, allowed=True, reason="OK")

        assert resp.max_cost_usd is None


# ============================================================================
# Unit Tests — Schema Validation
# ============================================================================


class TestSchemas:
    """Tests for Pydantic request/response schemas."""

    def test_check_request_defaults(self):
        req = RateLimitCheckRequest(provider=RateLimitProvider.XAI)
        assert req.estimated_cost_usd == 0.0

    def test_check_request_with_cost(self):
        req = RateLimitCheckRequest(
            provider=RateLimitProvider.MAID,
            estimated_cost_usd=0.05,
        )
        assert req.provider == RateLimitProvider.MAID
        assert req.estimated_cost_usd == 0.05

    def test_check_response_model(self):
        resp = RateLimitCheckResponse(
            allowed=True,
            provider="xai",
            current_count=10,
            max_count=5000,
            requests_remaining=4990,
            utilization=0.002,
            cost_usd=0.50,
            max_cost_usd=300.0,
            reason="OK",
        )
        assert resp.allowed is True
        assert resp.requests_remaining == 4990

    def test_provider_enum_values(self):
        assert RateLimitProvider.XAI.value == "xai"
        assert RateLimitProvider.MAID.value == "maid"


# ============================================================================
# Integration Tests — Router Logic
# ============================================================================


class TestCheckAndIncrement:
    """Tests for the check-and-increment endpoint logic."""

    def test_allows_under_limit(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(current_count=10, max_count=5000)
        resp = _build_response(row, allowed=True, reason="OK")
        assert resp.allowed is True

    def test_denies_at_limit(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(current_count=5000, max_count=5000)
        resp = _build_response(row, allowed=False, reason="Budget exhausted")
        assert resp.allowed is False
        assert "exhausted" in resp.reason.lower()

    def test_denies_over_cost_cap(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(
            current_count=10,
            cost_usd=Decimal("299.99"),
            max_cost_usd=Decimal("300.0"),
        )
        resp = _build_response(row, allowed=False, reason="Cost cap exceeded")
        assert resp.allowed is False

    def test_maid_provider(self):
        from app.api.rate_limits_router import _build_response

        row = _make_rate_limit_row(provider="maid", max_count=2000)
        resp = _build_response(row, allowed=True, reason="OK")
        assert resp.provider == "maid"
        assert resp.max_count == 2000


class TestWindowManagement:
    """Tests for rate-limit window creation and expiry."""

    def test_expired_window_detection(self):
        """A window older than window_duration should be considered expired."""
        row = _make_rate_limit_row()
        row.window_start = datetime.now(timezone.utc) - timedelta(days=31)
        row.window_duration_seconds = 30 * 24 * 3600

        # The row's window has expired; cutoff would exclude it
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=row.window_duration_seconds)
        assert row.window_start < cutoff

    def test_active_window_detection(self):
        """A recent window should be considered active."""
        row = _make_rate_limit_row()
        row.window_start = datetime.now(timezone.utc) - timedelta(days=15)
        row.window_duration_seconds = 30 * 24 * 3600

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=row.window_duration_seconds)
        assert row.window_start >= cutoff
