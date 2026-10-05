"""Checks for the runtime-promotion schema repair (revision 20261005_01).

Driven by scripts/prove_runtime_promotion_schema_repair_postgres.sh inside a throwaway cluster.
It never reads a configured or production database.

Usage: python -m scripts.prove_runtime_promotion_schema_repair_postgres <check>
Checks: schema_matches_models, row_survives, partial_is_refused_unchanged
"""

from __future__ import annotations

import os
import sys

import sqlalchemy as sa

from app.database import Base
from app.models import runtime_promotion_candidate_models  # noqa: F401
from app.models import runtime_promotion_models  # noqa: F401
from app.runtime_promotion.execution_handoff import models as _handoff_models  # noqa: F401

TABLES = (
    "runtime_promotion_receipts",
    "runtime_promotion_candidates",
    "runtime_promotion_candidate_decisions",
    "runtime_promotion_approval_decisions",
    "runtime_promotion_execution_requests",
    "runtime_promotion_execution_statuses",
    "runtime_promotion_verification_results",
)


def _engine() -> sa.Engine:
    url = os.environ["DATAFORGE_DATABASE_URL"]
    if "PGHOST" not in os.environ:
        raise SystemExit("Run through pg_virtualenv. Refusing to use a configured database.")
    return sa.create_engine(url)


def schema_matches_models() -> None:
    engine = _engine()
    insp = sa.inspect(engine)
    problems: list[str] = []
    notes: list[str] = []
    with engine.connect() as conn:
        for name in TABLES:
            if not insp.has_table(name):
                problems.append(f"{name}: missing")
                continue
            model = Base.metadata.tables[name]
            live_cols = {c["name"] for c in insp.get_columns(name)}
            if live_cols != {c.name for c in model.columns}:
                problems.append(f"{name}: columns differ {sorted(live_cols ^ {c.name for c in model.columns})}")
            live_idx = {i["name"] for i in insp.get_indexes(name)}
            model_idx = {i.name for i in model.indexes}
            # The original migrations never created some indexes that the models declare. That
            # drift is older than the repair. It is reported, not failed. See KNOWN_ISSUES.
            if not model_idx <= live_idx:
                notes.append(f"{name}: model-only indexes {sorted(model_idx - live_idx)}")
            if not live_idx:
                problems.append(f"{name}: no indexes created")
            live_fk = {
                (tuple(f["constrained_columns"]), f["referred_table"]) for f in insp.get_foreign_keys(name)
            }
            model_fk = {
                ((col.name,), fk.column.table.name) for col in model.columns for fk in col.foreign_keys
            }
            if live_fk != model_fk:
                problems.append(f"{name}: foreign keys differ")
            rls = conn.execute(
                sa.text("SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:t)"), {"t": name}
            ).scalar()
            policies = conn.execute(
                sa.text("SELECT count(*) FROM pg_policy WHERE polrelid = to_regclass(:t)"), {"t": name}
            ).scalar()
            if rls is not True or policies != 0:
                problems.append(f"{name}: expected RLS on with no policy, got rls={rls} policies={policies}")
    if problems:
        raise SystemExit("SCHEMA_CHECK_FAILED\n" + "\n".join(problems))
    for note in notes:
        print("NOTE", note)
    print("schema_matches_models OK: 7 tables, columns, foreign keys, RLS")


def seed_row() -> None:
    with _engine().begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO runtime_promotion_candidates "
                "(candidate_id, receipt_id, candidate_type, source_envelope_type, service, fleet_member_id, "
                "issue_class, severity, title, summary, evidence, source_payload) "
                "VALUES ('c-proof-1','r-1','t','e','s','f','i','low','title','summary','{}','{}')"
            )
        )
    print("seeded 1 candidate row")


def row_survives() -> None:
    with _engine().connect() as conn:
        count = conn.execute(sa.text("SELECT count(*) FROM runtime_promotion_candidates")).scalar()
    if count != 1:
        raise SystemExit(f"ROW_CHECK_FAILED: expected 1 candidate row, found {count}")
    print("row_survives OK: the repair re-run kept the existing row")


def partial_is_refused_unchanged() -> None:
    insp = sa.inspect(_engine())
    present = {t for t in TABLES if insp.has_table(t)}
    expected = set(TABLES) - {"runtime_promotion_execution_statuses"}
    if present != expected:
        raise SystemExit(f"PARTIAL_CHECK_FAILED: tables after the refused run: {sorted(present)}")
    print("partial_is_refused_unchanged OK: the refused run created and dropped nothing")


CHECKS = {
    "schema_matches_models": schema_matches_models,
    "seed_row": seed_row,
    "row_survives": row_survives,
    "partial_is_refused_unchanged": partial_is_refused_unchanged,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        raise SystemExit(__doc__)
    CHECKS[sys.argv[1]]()
