"""repair the runtime-promotion schema where its tables are missing

Revision ID: 20261005_01
Revises: 20260930_01
Create Date: 2026-10-05

On 2026-10-05 a read-only audit of the live database found all seven runtime-promotion tables
absent while `alembic_version` said 20260930_01. A deploy cannot restore them, because Alembic
trusts the stored revision. Proposal: docs/proposals/runtime_promotion_schema_repair.md.

This migration replays the five original migrations that created the family, one group at a time:

- A group whose tables are all absent runs the original `upgrade()` unchanged. The original code is the
  single source for columns, constraints, foreign keys and indexes.
- A group whose tables are all present is left alone.
- A group with only some of its tables present stops the migration with an error. It does not alter anything.

It then enables row-level security, with no policies, on all seven tables. This is the same deny-all
posture as 20260711_01. The owner role that the app uses still bypasses it.

It never stamps, drops or rewrites data. The downgrade does nothing, because a downgrade must not drop tables
that may hold data.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic import context, op

revision = "20261005_01"
down_revision = "20260930_01"
branch_labels = None
depends_on = None

# (original migration file, the tables it creates), in dependency order.
_GROUPS = (
    (
        "6c7378d479d3_add_runtime_promotion_receipts.py",
        ("runtime_promotion_receipts",),
    ),
    (
        "75660723bef6_add_runtime_promotion_candidates_table.py",
        ("runtime_promotion_candidates",),
    ),
    (
        "20260401_1200_add_runtime_promotion_candidate_decisions.py",
        ("runtime_promotion_candidate_decisions",),
    ),
    (
        "20260401_01_runtime_promotion_execution_handoff.py",
        (
            "runtime_promotion_approval_decisions",
            "runtime_promotion_execution_requests",
            "runtime_promotion_execution_statuses",
        ),
    ),
    (
        "20260401_02_runtime_promotion_verification_closeout.py",
        ("runtime_promotion_verification_results",),
    ),
)

ALL_TABLES = tuple(table for _, tables in _GROUPS for table in tables)


def _load_original(filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"_rp_repair_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load the original migration {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError(
            "This repair must inspect the live schema. Run it online, not with --sql."
        )
    inspector = sa.inspect(op.get_bind())
    for filename, tables in _GROUPS:
        present = [t for t in tables if inspector.has_table(t)]
        if not present:
            _load_original(filename).upgrade()
        elif len(present) != len(tables):
            missing = [t for t in tables if t not in present]
            raise RuntimeError(
                "Partial runtime-promotion schema: "
                f"{', '.join(present)} exist but {', '.join(missing)} are missing. "
                "Repair by hand. This migration does not alter an existing table."
            )
    for table in ALL_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    # Intentionally empty: a downgrade must not drop tables that may hold data.
    pass
