"""create the durable ForgeAgents registry

The AgentRegistry ORM model and /api/v1/agents API have existed without an
Alembic migration.  Fresh databases therefore pass ``alembic upgrade head``
but the first registry request fails because ``agent_registry`` is absent.

Revision ID: 20260714_01
Revises: 20260712_03
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260714_01"
down_revision = "20260712_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_registry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("agent_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "agent_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_registry_agent_type",
        "agent_registry",
        ["agent_type"],
    )
    op.create_index(
        "ix_agent_registry_created_at",
        "agent_registry",
        ["created_at"],
    )
    op.create_index(
        "ix_agent_registry_name",
        "agent_registry",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_agent_registry_status",
        "agent_registry",
        ["status"],
    )
    op.create_index(
        "ix_agent_registry_user_id",
        "agent_registry",
        ["user_id"],
    )

    # Match the deny-by-default posture of every durable DataForge table.
    # The application owner role bypasses RLS; Supabase Data API roles do not.
    op.execute("ALTER TABLE public.agent_registry ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(
        "ix_agent_registry_user_id",
        table_name="agent_registry",
    )
    op.drop_index(
        "ix_agent_registry_status",
        table_name="agent_registry",
    )
    op.drop_index(
        "ix_agent_registry_name",
        table_name="agent_registry",
    )
    op.drop_index(
        "ix_agent_registry_created_at",
        table_name="agent_registry",
    )
    op.drop_index(
        "ix_agent_registry_agent_type",
        table_name="agent_registry",
    )
    op.drop_table("agent_registry")
