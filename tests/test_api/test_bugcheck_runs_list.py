"""Tests for the BugCheck run-listing endpoint (GET /api/v1/bugcheck/runs).

The list route backs ForgeAgents' GET /bugcheck/runs surface. DataForge is the
source of truth for runs, so listing must be served here rather than
reconstructed downstream.
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bugcheck_models import BugCheckRunModel


def _make_run(
    *,
    targets: list[str],
    status: str = "finalized",
    started_at: datetime,
    commit_sha: str = "a" * 40,
) -> BugCheckRunModel:
    return BugCheckRunModel(
        run_type="service_run",
        targets=targets,
        mode="standard",
        scope="full_repo",
        commit_sha=commit_sha,
        status=status,
        started_at=started_at,
        severity_counts={},
        gating_result="pass",
        checks_run=[],
    )


def _seed(db: Session, runs: list[BugCheckRunModel]) -> None:
    for run in runs:
        db.add(run)
    db.commit()


def test_list_runs_returns_newest_first(client: TestClient, db: Session) -> None:
    base = datetime(2026, 1, 1, 12, 0, 0)
    _seed(
        db,
        [
            _make_run(targets=["neuroforge"], started_at=base),
            _make_run(targets=["dataforge"], started_at=base + timedelta(hours=1)),
            _make_run(targets=["rake"], started_at=base + timedelta(hours=2)),
        ],
    )

    resp = client.get("/api/v1/bugcheck/runs")
    assert resp.status_code == 200

    body = resp.json()
    assert len(body) == 3
    # Newest started_at first.
    assert body[0]["targets"] == ["rake"]
    assert body[1]["targets"] == ["dataforge"]
    assert body[2]["targets"] == ["neuroforge"]


def test_list_runs_respects_limit(client: TestClient, db: Session) -> None:
    base = datetime(2026, 2, 1, 12, 0, 0)
    _seed(
        db,
        [
            _make_run(targets=["svc"], started_at=base + timedelta(minutes=i))
            for i in range(5)
        ],
    )

    resp = client.get("/api/v1/bugcheck/runs", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_runs_filters_by_status(client: TestClient, db: Session) -> None:
    base = datetime(2026, 3, 1, 12, 0, 0)
    _seed(
        db,
        [
            _make_run(targets=["a"], status="running", started_at=base),
            _make_run(
                targets=["b"], status="finalized", started_at=base + timedelta(hours=1)
            ),
        ],
    )

    resp = client.get("/api/v1/bugcheck/runs", params={"status": "running"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "running"


def test_list_runs_filters_by_target_membership(
    client: TestClient, db: Session
) -> None:
    base = datetime(2026, 4, 1, 12, 0, 0)
    _seed(
        db,
        [
            _make_run(targets=["neuroforge", "dataforge"], started_at=base),
            _make_run(targets=["rake"], started_at=base + timedelta(hours=1)),
        ],
    )

    resp = client.get("/api/v1/bugcheck/runs", params={"target": "dataforge"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "dataforge" in body[0]["targets"]


def test_list_runs_empty_when_no_runs(client: TestClient, db: Session) -> None:
    resp = client.get("/api/v1/bugcheck/runs")
    assert resp.status_code == 200
    assert resp.json() == []
