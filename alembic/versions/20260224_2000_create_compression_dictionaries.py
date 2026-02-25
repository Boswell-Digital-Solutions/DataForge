"""Create compression_dictionaries table for Zstd dictionary governance.

Revision ID: compression_dict_001
Revises: rate_limits_001
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "compression_dict_001"
down_revision: Union[str, Sequence[str], None] = "rate_limits_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compression_dictionaries",
        sa.Column("dictionary_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("service_pair", sa.String(100), nullable=False, comment="e.g. forgeagents-dataforge"),
        sa.Column("payload_class", sa.String(100), nullable=False, comment="e.g. experience_search_response"),
        sa.Column("schema_version_min", sa.String(20), nullable=True),
        sa.Column("schema_version_max", sa.String(20), nullable=True),
        sa.Column("algorithm", sa.String(20), nullable=False, server_default="zstd"),
        sa.Column("dictionary_size_bytes", sa.Integer, nullable=False),
        sa.Column("dictionary_blob", sa.LargeBinary, nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("training_sample_n", sa.Integer, nullable=False),
        sa.Column("training_params", JSONB, nullable=True),
        sa.Column("compression_ratio", sa.Float, nullable=True, comment="Measured ratio on test set"),
        sa.Column(
            "program",
            sa.String(20),
            nullable=False,
            comment="transport or archive",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="TRAINING",
            comment="TRAINING, CANDIDATE, ACTIVE, RETIRED",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial unique index: only one ACTIVE dictionary per (service_pair, payload_class, schema_version_max, program)
    op.create_index(
        "uq_active_dict_per_pair_class_program",
        "compression_dictionaries",
        ["service_pair", "payload_class", "schema_version_max", "program"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_index(
        "ix_compression_dict_service_pair",
        "compression_dictionaries",
        ["service_pair"],
    )

    op.create_index(
        "ix_compression_dict_status",
        "compression_dictionaries",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_compression_dict_status")
    op.drop_index("ix_compression_dict_service_pair")
    op.drop_index("uq_active_dict_per_pair_class_program")
    op.drop_table("compression_dictionaries")
