"""CSSA Phase 6 gate (DataForge side): atomic quota + durable single-use ledger."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer test-service-token"}
FUTURE = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
PAST = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()


def reservation(rid: str = "qr-1", units: int = 100, expires_at: str = FUTURE) -> dict[str, Any]:
    return {
        "schema_version": "cloud_security.quota_reservation.v1",
        "quota_reservation_id": rid,
        "tenant_id": "ten_forge",
        "principal_id": "usr_charlie",
        "service": "neuroforge",
        "quota_bucket": "neuroforge.tokens.daily",
        "reserved_units": units,
        "unit_type": "tokens",
        "expires_at": expires_at,
        "status": "reserved",
    }


def reserve(client: TestClient, payload: dict[str, Any], limit: int = 1000) -> Any:
    return client.post(
        "/api/v1/cloud-security/quota/reserve",
        json={"payload": payload, "bucket_limit": limit},
        headers=AUTH,
    )


class TestAtomicReservation:
    def test_reserve_within_limit(self, client: TestClient):
        r = reserve(client, reservation())
        assert r.status_code == 201
        assert r.json()["reservation"]["status"] == "reserved"

    def test_cannot_overspend_bucket(self, client: TestClient):
        # limit 1000; ten reserves of 150 -> exactly 6 fit (900), the rest 409
        results = [
            reserve(client, reservation(rid=f"qr-{i}", units=150)).status_code
            for i in range(10)
        ]
        assert results.count(201) == 6
        assert results.count(409) == 4
        usage = client.get(
            "/api/v1/cloud-security/quota/buckets/neuroforge.tokens.daily/usage",
            headers=AUTH,
        ).json()
        assert usage["active_units"] == 900  # never exceeds the limit

    def test_quota_exceeded_reason_in_detail(self, client: TestClient):
        reserve(client, reservation(rid="qr-a", units=900))
        denied = reserve(client, reservation(rid="qr-b", units=200))
        assert denied.status_code == 409
        assert "QUOTA_EXCEEDED" in denied.json()["detail"]

    def test_idempotent_retry(self, client: TestClient):
        payload = reservation()
        assert reserve(client, payload).status_code == 201
        retry = reserve(client, payload)
        assert retry.status_code == 201 or retry.json().get("idempotent_retry")


class TestLifecycle:
    def test_commit_actual_releases_remainder(self, client: TestClient):
        reserve(client, reservation(units=500))
        r = client.post(
            "/api/v1/cloud-security/quota/qr-1/commit",
            json={"actual_units": 120},
            headers=AUTH,
        )
        assert r.status_code == 200
        assert r.json()["reservation"]["committed_units"] == 120
        usage = client.get(
            "/api/v1/cloud-security/quota/buckets/neuroforge.tokens.daily/usage",
            headers=AUTH,
        ).json()
        assert usage["active_units"] == 120  # remainder no longer counted

    def test_commit_cannot_exceed_reserved(self, client: TestClient):
        reserve(client, reservation(units=100))
        r = client.post(
            "/api/v1/cloud-security/quota/qr-1/commit",
            json={"actual_units": 150},
            headers=AUTH,
        )
        assert r.status_code == 409

    def test_release(self, client: TestClient):
        reserve(client, reservation(units=400))
        r = client.post("/api/v1/cloud-security/quota/qr-1/release", headers=AUTH)
        assert r.status_code == 200
        usage = client.get(
            "/api/v1/cloud-security/quota/buckets/neuroforge.tokens.daily/usage",
            headers=AUTH,
        ).json()
        assert usage["active_units"] == 0

    def test_abandoned_reservation_expires_via_reconcile(self, client: TestClient):
        reserve(client, reservation(rid="qr-stale", units=300, expires_at=PAST))
        r = client.post("/api/v1/cloud-security/quota/reconcile", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["expired"] == 1
        # the expired reservation frees its bucket capacity
        assert reserve(client, reservation(rid="qr-new", units=1000)).status_code == 201

    def test_expired_reservation_not_counted_even_before_reconcile(self, client: TestClient):
        reserve(client, reservation(rid="qr-stale", units=900, expires_at=PAST))
        ok = reserve(client, reservation(rid="qr-live", units=900))
        assert ok.status_code == 201  # stale reservation does not block


class TestDurableConsumption:
    def test_consume_once_then_replay_409(self, client: TestClient):
        first = client.post(
            "/api/v1/cloud-security/authorizations/auth-1/consume", headers=AUTH
        )
        replay = client.post(
            "/api/v1/cloud-security/authorizations/auth-1/consume", headers=AUTH
        )
        assert first.status_code == 201
        assert replay.status_code == 409
        assert "single-use" in replay.json()["detail"]

    def test_requires_bearer(self, client: TestClient):
        r = client.post("/api/v1/cloud-security/authorizations/auth-2/consume")
        assert r.status_code == 401
