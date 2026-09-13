"""create durable NeuroForge cloud-image state and outbox

Revision ID: 20260913_01
Revises: 20260906_01
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260913_01"
down_revision = "20260906_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cloud_image_jobs",
        sa.Column("job_id", sa.String(96), primary_key=True),
        sa.Column("request_id", sa.String(96), nullable=False),
        sa.Column("caller_identity", sa.String(256), nullable=False),
        sa.Column("idempotency_key", sa.String(256), nullable=False),
        sa.Column("correlation_id", sa.String(256), nullable=False),
        sa.Column("source_service", sa.String(128), nullable=False),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("use_case", sa.String(96), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("provider_override", sa.String(64), nullable=True),
        sa.Column("policy_block_code", sa.String(128), nullable=True),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("accepted_final_count", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("replacement_round", sa.Integer(), nullable=False),
        sa.Column("max_replacement_rounds", sa.Integer(), nullable=False),
        sa.Column("max_total_candidates", sa.Integer(), nullable=False),
        sa.Column("max_cost_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("fulfillment_limits_exhausted", sa.Boolean(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("record_payload", sa.JSON(), nullable=False),
        sa.CheckConstraint("requested_count BETWEEN 1 AND 12", name="ck_cloud_image_requested_count"),
        sa.CheckConstraint("accepted_final_count >= 0", name="ck_cloud_image_accepted_count"),
        sa.CheckConstraint("candidate_count >= 0", name="ck_cloud_image_candidate_count"),
        sa.CheckConstraint("replacement_round >= 0", name="ck_cloud_image_replacement_round"),
        sa.CheckConstraint("row_version >= 1", name="ck_cloud_image_row_version"),
    )
    op.create_index("ix_cloud_image_jobs_request_id", "cloud_image_jobs", ["request_id"], unique=True)
    op.create_index("ix_cloud_image_jobs_caller_identity", "cloud_image_jobs", ["caller_identity"])
    op.create_index("ix_cloud_image_jobs_correlation_id", "cloud_image_jobs", ["correlation_id"])
    op.create_index("ix_cloud_image_jobs_app_id", "cloud_image_jobs", ["app_id"])
    op.create_index("ix_cloud_image_jobs_status", "cloud_image_jobs", ["status"])

    op.create_table(
        "cloud_image_protected_requests",
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("schema_version", sa.String(128), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False),
        sa.Column("key_ref", sa.String(256), nullable=False),
        sa.Column("nonce_b64", sa.String(64), nullable=False),
        sa.Column("aad_b64", sa.String(512), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("ciphertext_sha256", sa.String(71), nullable=False),
        sa.Column("semantic_request_fingerprint", sa.String(76), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("algorithm = 'A256GCM'", name="ck_cloud_image_protected_algorithm"),
    )

    op.create_table(
        "cloud_image_idempotency_bindings",
        sa.Column("binding_id", sa.String(96), primary_key=True),
        sa.Column("caller_identity", sa.String(256), nullable=False),
        sa.Column("idempotency_key", sa.String(256), nullable=False),
        sa.Column("semantic_request_fingerprint", sa.String(76), nullable=False),
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "caller_identity",
            "idempotency_key",
            name="uq_cloud_image_idempotency_scope",
        ),
    )
    op.create_index("ix_cloud_image_idempotency_bindings_job_id", "cloud_image_idempotency_bindings", ["job_id"])

    op.create_table(
        "cloud_image_operation_receipts",
        sa.Column("operation_id", sa.String(128), primary_key=True),
        sa.Column("operation_kind", sa.String(32), nullable=False),
        sa.Column("operation_fingerprint", sa.String(76), nullable=False),
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resulting_row_version", sa.Integer(), nullable=False),
        sa.Column("resulting_status", sa.String(64), nullable=False),
        sa.Column("resulting_record_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cloud_image_operation_receipts_job_id", "cloud_image_operation_receipts", ["job_id"])

    op.create_table(
        "cloud_image_events",
        sa.Column("event_id", sa.String(96), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("caller_identity", sa.String(256), nullable=False),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(256), nullable=False),
        sa.Column(
            "job_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cloud_image_events_event_type", "cloud_image_events", ["event_type"])
    op.create_index("ix_cloud_image_events_correlation_id", "cloud_image_events", ["correlation_id"])
    op.create_index("ix_cloud_image_events_job_id", "cloud_image_events", ["job_id"])
    op.create_index("ix_cloud_image_events_created_at", "cloud_image_events", ["created_at"])

    op.create_table(
        "cloud_image_outbox",
        sa.Column("outbox_id", sa.String(96), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(96),
            sa.ForeignKey("cloud_image_events.event_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("aggregate_id", sa.String(96), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False),
        sa.CheckConstraint("delivery_attempts >= 0", name="ck_cloud_image_outbox_attempts"),
    )
    op.create_index("ix_cloud_image_outbox_aggregate_id", "cloud_image_outbox", ["aggregate_id"])
    op.create_index("ix_cloud_image_outbox_published_at", "cloud_image_outbox", ["published_at"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (
            "cloud_image_jobs",
            "cloud_image_protected_requests",
            "cloud_image_idempotency_bindings",
            "cloud_image_operation_receipts",
            "cloud_image_events",
            "cloud_image_outbox",
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
    op.drop_index("ix_cloud_image_outbox_published_at", table_name="cloud_image_outbox")
    op.drop_index("ix_cloud_image_outbox_aggregate_id", table_name="cloud_image_outbox")
    op.drop_table("cloud_image_outbox")
    op.drop_index("ix_cloud_image_events_created_at", table_name="cloud_image_events")
    op.drop_index("ix_cloud_image_events_job_id", table_name="cloud_image_events")
    op.drop_index("ix_cloud_image_events_correlation_id", table_name="cloud_image_events")
    op.drop_index("ix_cloud_image_events_event_type", table_name="cloud_image_events")
    op.drop_table("cloud_image_events")
    op.drop_index("ix_cloud_image_operation_receipts_job_id", table_name="cloud_image_operation_receipts")
    op.drop_table("cloud_image_operation_receipts")
    op.drop_index("ix_cloud_image_idempotency_bindings_job_id", table_name="cloud_image_idempotency_bindings")
    op.drop_table("cloud_image_idempotency_bindings")
    op.drop_table("cloud_image_protected_requests")
    op.drop_index("ix_cloud_image_jobs_status", table_name="cloud_image_jobs")
    op.drop_index("ix_cloud_image_jobs_app_id", table_name="cloud_image_jobs")
    op.drop_index("ix_cloud_image_jobs_correlation_id", table_name="cloud_image_jobs")
    op.drop_index("ix_cloud_image_jobs_caller_identity", table_name="cloud_image_jobs")
    op.drop_index("ix_cloud_image_jobs_request_id", table_name="cloud_image_jobs")
    op.drop_table("cloud_image_jobs")
