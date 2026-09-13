"""add leased cloud-image recovery and rebuildable outbox delivery

Revision ID: 20260913_02
Revises: 20260913_01
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260913_02"
down_revision = "20260913_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cloud_image_outbox",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "cloud_image_outbox",
        sa.Column("claim_owner", sa.String(128), nullable=True),
    )
    op.add_column(
        "cloud_image_outbox",
        sa.Column("claim_token", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "cloud_image_outbox",
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cloud_image_outbox",
        sa.Column("last_error_code", sa.String(128), nullable=True),
    )
    op.add_column(
        "cloud_image_outbox",
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_cloud_image_outbox_next_attempt_at",
        "cloud_image_outbox",
        ["next_attempt_at"],
    )
    op.create_index(
        "ix_cloud_image_outbox_claim_expires_at",
        "cloud_image_outbox",
        ["claim_expires_at"],
    )
    op.create_index(
        "ix_cloud_image_outbox_dead_lettered_at",
        "cloud_image_outbox",
        ["dead_lettered_at"],
    )

    op.create_table(
        "cloud_image_leases",
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("worker_id", sa.String(128), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(128), nullable=True),
        sa.CheckConstraint("fencing_token >= 1", name="ck_cloud_image_lease_token"),
    )
    op.create_index(
        "ix_cloud_image_leases_worker_id", "cloud_image_leases", ["worker_id"]
    )
    op.create_index(
        "ix_cloud_image_leases_expires_at", "cloud_image_leases", ["expires_at"]
    )

    op.create_table(
        "cloud_image_stage_attempts",
        sa.Column("attempt_id", sa.String(128), primary_key=True),
        sa.Column("operation_id", sa.String(128), nullable=False, unique=True),
        sa.Column("operation_fingerprint", sa.String(76), nullable=False),
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("retry_class", sa.String(32), nullable=False),
        sa.Column("failure_code", sa.String(128), nullable=True),
        sa.Column("result_digest", sa.String(71), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transitioned_to_status", sa.String(64), nullable=True),
        sa.Column("transitioned_row_version", sa.Integer(), nullable=True),
        sa.Column("transitioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number >= 1", name="ck_cloud_image_attempt_number"),
        sa.CheckConstraint("fencing_token >= 1", name="ck_cloud_image_attempt_token"),
        sa.UniqueConstraint(
            "job_id",
            "stage",
            "attempt_number",
            name="uq_cloud_image_stage_attempt_number",
        ),
    )
    op.create_index(
        "ix_cloud_image_stage_attempts_job_id",
        "cloud_image_stage_attempts",
        ["job_id"],
    )
    op.create_index(
        "ix_cloud_image_stage_attempts_stage",
        "cloud_image_stage_attempts",
        ["stage"],
    )
    op.create_index(
        "ix_cloud_image_stage_attempts_status",
        "cloud_image_stage_attempts",
        ["status"],
    )
    op.create_index(
        "ix_cloud_image_stage_attempts_next_attempt_at",
        "cloud_image_stage_attempts",
        ["next_attempt_at"],
    )

    op.create_table(
        "cloud_image_control_receipts",
        sa.Column("operation_id", sa.String(128), primary_key=True),
        sa.Column("operation_kind", sa.String(48), nullable=False),
        sa.Column("operation_fingerprint", sa.String(76), nullable=False),
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_cloud_image_control_receipts_job_id",
        "cloud_image_control_receipts",
        ["job_id"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (
            "cloud_image_leases",
            "cloud_image_stage_attempts",
            "cloud_image_control_receipts",
        ):
            op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
            op.execute(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM anon';
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM authenticated';
                    END IF;
                END
                $$;
                """
            )


def downgrade() -> None:
    op.drop_index(
        "ix_cloud_image_control_receipts_job_id",
        table_name="cloud_image_control_receipts",
    )
    op.drop_table("cloud_image_control_receipts")
    op.drop_index(
        "ix_cloud_image_stage_attempts_next_attempt_at",
        table_name="cloud_image_stage_attempts",
    )
    op.drop_index(
        "ix_cloud_image_stage_attempts_status",
        table_name="cloud_image_stage_attempts",
    )
    op.drop_index(
        "ix_cloud_image_stage_attempts_stage",
        table_name="cloud_image_stage_attempts",
    )
    op.drop_index(
        "ix_cloud_image_stage_attempts_job_id",
        table_name="cloud_image_stage_attempts",
    )
    op.drop_table("cloud_image_stage_attempts")
    op.drop_index("ix_cloud_image_leases_expires_at", table_name="cloud_image_leases")
    op.drop_index("ix_cloud_image_leases_worker_id", table_name="cloud_image_leases")
    op.drop_table("cloud_image_leases")
    op.drop_index(
        "ix_cloud_image_outbox_dead_lettered_at", table_name="cloud_image_outbox"
    )
    op.drop_index(
        "ix_cloud_image_outbox_claim_expires_at", table_name="cloud_image_outbox"
    )
    op.drop_index(
        "ix_cloud_image_outbox_next_attempt_at", table_name="cloud_image_outbox"
    )
    op.drop_column("cloud_image_outbox", "dead_lettered_at")
    op.drop_column("cloud_image_outbox", "last_error_code")
    op.drop_column("cloud_image_outbox", "claim_expires_at")
    op.drop_column("cloud_image_outbox", "claim_token")
    op.drop_column("cloud_image_outbox", "claim_owner")
    op.drop_column("cloud_image_outbox", "next_attempt_at")
