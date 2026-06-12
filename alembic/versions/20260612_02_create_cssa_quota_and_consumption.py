"""create CSSA quota reservations + durable authorization consumption ledger

Atomic quota reservation persistence is DataForge-owned (authority plan §13,
§30; OPEN-3). Reservations are atomic per quota bucket: the reserve endpoint
sums unexpired reserved + committed units inside one transaction (with a
per-bucket advisory lock on PostgreSQL) so concurrent reserves cannot
overspend. cssa_authorization_consumptions is the durable single-use ledger:
an authorization consumed once is consumed forever, across process restarts.

Revision ID: 20260612_02
Revises: 20260612_01
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "20260612_02"
down_revision = "20260612_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cssa_quota_reservations",
        sa.Column("quota_reservation_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=True),
        sa.Column("principal_id", sa.String(128), nullable=False),
        sa.Column("service", sa.String(128), nullable=False),
        sa.Column("quota_bucket", sa.String(256), nullable=False),
        sa.Column("reserved_units", sa.BigInteger(), nullable=False),
        sa.Column("committed_units", sa.BigInteger(), nullable=True),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_cssa_quota_reservations_bucket_status",
        "cssa_quota_reservations",
        ["quota_bucket", "status"],
    )

    op.create_table(
        "cssa_authorization_consumptions",
        sa.Column("authorization_id", sa.String(128), primary_key=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("cssa_authorization_consumptions")
    op.drop_table("cssa_quota_reservations")
