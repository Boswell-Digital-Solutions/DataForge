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


revision = "20260714_01"
down_revision = "20260712_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS public.agent_registry (
                id VARCHAR(36) NOT NULL,
                name VARCHAR(100) NOT NULL,
                agent_type VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL,
                user_id VARCHAR(36),
                agent_data JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (id)
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_agent_registry_agent_type
            ON public.agent_registry (agent_type)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_agent_registry_created_at
            ON public.agent_registry (created_at)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_registry_name
            ON public.agent_registry (name)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_agent_registry_status
            ON public.agent_registry (status)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_agent_registry_user_id
            ON public.agent_registry (user_id)
            """
        )
    )

    # Match the deny-by-default posture of every durable DataForge table.
    # The application owner role bypasses RLS; Supabase Data API roles do not.
    conn.execute(sa.text("ALTER TABLE public.agent_registry ENABLE ROW LEVEL SECURITY"))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_agent_registry_user_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_agent_registry_status"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_agent_registry_name"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_agent_registry_created_at"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_agent_registry_agent_type"))
    conn.execute(sa.text("DROP TABLE IF EXISTS public.agent_registry"))
