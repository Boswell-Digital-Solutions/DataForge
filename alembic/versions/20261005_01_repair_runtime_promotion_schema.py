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
- A group whose tables are all present is left alone, but only after its shape matches what the original
  migration creates: column names, types and nullability, the primary key, foreign keys, unique constraints
  and indexes. A table with the wrong shape stops the migration.
- A group with only some of its tables present stops the migration with an error.

All checks run before any change. A failed check alters nothing.

It then enables row-level security on all seven tables. Enabling RLS keeps existing policies, so the migration
first rejects any policy on these tables. That guarantees the deny-all posture of 20260711_01. The owner role
that the app uses still bypasses RLS.

It never stamps, drops or rewrites data. The downgrade does nothing, because a downgrade must not drop tables
that may hold data.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

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


def _load_original(filename: str, op_override=None):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"_rp_repair_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load the original migration {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if op_override is not None:
        module.op = op_override
    return module


class _Recorder:
    """Stands in for `op` while an original upgrade() runs. It records what the migration would create."""

    def __init__(self) -> None:
        self.tables: dict[str, tuple] = {}
        self.indexes: list[tuple[str, str, tuple[str, ...], bool]] = []

    def f(self, name: str) -> str:
        return name

    def create_table(self, name: str, *items, **_kw) -> None:
        self.tables[name] = items

    def create_index(self, name, table, columns, unique=False, **_kw) -> None:
        self.indexes.append((name, table, tuple(columns), bool(unique)))

    def __getattr__(self, attr: str):
        raise RuntimeError(f"Unexpected operation op.{attr} in an original runtime-promotion migration")


def _canonical_type(type_) -> str:
    return type_.compile(dialect=postgresql.dialect()).upper()


def _constraint_columns(item) -> tuple[str, ...]:
    """Column names of a constraint that is not attached to a table yet."""
    pending = getattr(item, "_pending_colargs", None)
    raw = pending if pending else list(item.columns)
    return tuple(c if isinstance(c, str) else c.name for c in raw)


def _shape_problems(inspector, table: str, items: tuple, indexes: list) -> list[str]:
    problems: list[str] = []
    columns = [i for i in items if isinstance(i, sa.Column)]
    live = {c["name"]: c for c in inspector.get_columns(table)}
    if set(live) != {c.name for c in columns}:
        problems.append(f"{table}: columns differ {sorted(set(live) ^ {c.name for c in columns})}")
    for col in columns:
        found = live.get(col.name)
        if found is None:
            continue
        if _canonical_type(col.type) != _canonical_type(found["type"]):
            problems.append(
                f"{table}.{col.name}: type {_canonical_type(found['type'])}, expected {_canonical_type(col.type)}"
            )
        if bool(found["nullable"]) != (bool(col.nullable) and not col.primary_key):
            problems.append(f"{table}.{col.name}: nullability differs")
    expected_pk = {c.name for c in columns if c.primary_key}
    for item in items:
        if isinstance(item, sa.PrimaryKeyConstraint):
            expected_pk |= set(_constraint_columns(item))
    live_pk = set(inspector.get_pk_constraint(table).get("constrained_columns") or [])
    if live_pk != expected_pk:
        problems.append(f"{table}: primary key {sorted(live_pk)}, expected {sorted(expected_pk)}")
    expected_fk = set()
    for item in items:
        if isinstance(item, sa.ForeignKeyConstraint):
            targets = [e.target_fullname.split(".") for e in item.elements]
            expected_fk.add(
                (
                    tuple(item.column_keys),
                    targets[0][0],
                    tuple(t[-1] for t in targets),
                    str(item.ondelete or "").upper(),
                )
            )
    live_fk = {
        (
            tuple(f["constrained_columns"]),
            f["referred_table"],
            tuple(f["referred_columns"]),
            str((f.get("options") or {}).get("ondelete") or "").upper(),
        )
        for f in inspector.get_foreign_keys(table)
    }
    if live_fk != expected_fk:
        problems.append(f"{table}: foreign keys {sorted(live_fk)}, expected {sorted(expected_fk)}")
    live_unique = {tuple(u["column_names"]) for u in inspector.get_unique_constraints(table)}
    live_indexes = {(tuple(i["column_names"]), bool(i["unique"])) for i in inspector.get_indexes(table)}
    live_unique |= {cols for cols, unique in live_indexes if unique}
    expected_unique = {(c.name,) for c in columns if c.unique}
    for item in items:
        if isinstance(item, sa.UniqueConstraint):
            expected_unique.add(_constraint_columns(item))
    for cols in expected_unique:
        if cols not in live_unique:
            problems.append(f"{table}: unique constraint on {cols} is missing")
    for _name, tbl, cols, unique in indexes:
        if tbl == table and (cols, unique) not in live_indexes:
            problems.append(f"{table}: index on {cols} (unique={unique}) is missing")
    return problems


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError(
            "This repair must inspect the live schema. Run it online, not with --sql."
        )
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Pass 1: decide. Nothing changes here.
    policies = bind.execute(
        sa.text(
            "SELECT c.relname, p.polname FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid "
            "WHERE c.relname = ANY(:tables)"
        ),
        {"tables": list(ALL_TABLES)},
    ).fetchall()
    if policies:
        raise RuntimeError(
            "Unexpected row-level-security policy on a runtime-promotion table: "
            + ", ".join(f"{r[0]}.{r[1]}" for r in policies)
            + ". Enabling RLS keeps policies, so the deny-all posture cannot be guaranteed. "
            "Remove or review the policy first."
        )
    to_create: list[str] = []
    for filename, tables in _GROUPS:
        present = [t for t in tables if inspector.has_table(t)]
        if not present:
            to_create.append(filename)
        elif len(present) != len(tables):
            missing = [t for t in tables if t not in present]
            raise RuntimeError(
                "Partial runtime-promotion schema: "
                f"{', '.join(present)} exist but {', '.join(missing)} are missing. "
                "Repair by hand. This migration does not alter an existing table."
            )
        else:
            recorder = _Recorder()
            _load_original(filename, recorder).upgrade()
            problems: list[str] = []
            for table in tables:
                problems += _shape_problems(inspector, table, recorder.tables[table], recorder.indexes)
            if problems:
                raise RuntimeError(
                    "Existing runtime-promotion table has the wrong shape. Nothing was changed.\n"
                    + "\n".join(problems)
                )

    # Pass 2: change.
    for filename in to_create:
        _load_original(filename).upgrade()
    for table in ALL_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    # Intentionally empty: a downgrade must not drop tables that may hold data.
    pass
