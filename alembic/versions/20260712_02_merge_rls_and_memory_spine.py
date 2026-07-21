"""merge heads (RLS drift-hardening pass + FMEM-02 memory spine)

20260711_01 and fmem02_memory_spine were authored in parallel against the same
prior head (20260623_01) and merged via separate PRs (#25, #26), producing two
divergent heads. Pure merge, no schema changes -- see 20260712_03 for the
follow-up that brings the memory spine tables in line with 20260711_01's RLS
posture.

Revision ID: 20260712_02
Revises: 20260711_01, fmem02_memory_spine
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_02"
down_revision = ("20260711_01", "fmem02_memory_spine")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
