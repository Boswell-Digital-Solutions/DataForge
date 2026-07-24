"""isolate canonical telemetry ingest behind a least-privilege role

Revision ID: 20260724_02
Revises: 20260724_01
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260724_02"
down_revision: str | None = "20260724_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $role$
        DECLARE
            existing pg_roles%ROWTYPE;
        BEGIN
            SELECT *
            INTO existing
            FROM pg_roles
            WHERE rolname = 'dataforge_telemetry_ingest';

            IF NOT FOUND THEN
                CREATE ROLE dataforge_telemetry_ingest
                    NOLOGIN
                    NOSUPERUSER
                    NOCREATEDB
                    NOCREATEROLE
                    NOREPLICATION
                    NOBYPASSRLS;
            ELSIF existing.rolcanlogin
                OR existing.rolsuper
                OR existing.rolcreatedb
                OR existing.rolcreaterole
                OR existing.rolreplication
                OR existing.rolbypassrls
            THEN
                RAISE EXCEPTION
                    'dataforge_telemetry_ingest role is not least privilege';
            END IF;
        END
        $role$
        """
    )
    op.execute(
        "GRANT USAGE ON SCHEMA public TO dataforge_telemetry_ingest"
    )
    op.execute(
        """
        GRANT SELECT, INSERT ON TABLE forge_events_v1
        TO dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        GRANT EXECUTE ON FUNCTION ingest_forge_event_v1(JSONB, CHAR(64))
        TO dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        GRANT EXECUTE ON FUNCTION
            forge_jsonb_object_values_are_numbers_v1(JSONB)
        TO dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        CREATE POLICY forge_events_v1_telemetry_insert
        ON forge_events_v1
        FOR INSERT
        TO dataforge_telemetry_ingest
        WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY forge_events_v1_telemetry_select
        ON forge_events_v1
        FOR SELECT
        TO dataforge_telemetry_ingest
        USING (true)
        """
    )


def downgrade() -> None:
    """Revoke ingress without deleting canonical evidence or login roles."""

    op.execute(
        """
        DROP POLICY IF EXISTS forge_events_v1_telemetry_select
        ON forge_events_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_events_v1_telemetry_insert
        ON forge_events_v1
        """
    )
    op.execute(
        """
        REVOKE EXECUTE ON FUNCTION
            forge_jsonb_object_values_are_numbers_v1(JSONB)
        FROM dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        REVOKE EXECUTE ON FUNCTION ingest_forge_event_v1(JSONB, CHAR(64))
        FROM dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        REVOKE SELECT, INSERT ON TABLE forge_events_v1
        FROM dataforge_telemetry_ingest
        """
    )
    op.execute(
        "REVOKE USAGE ON SCHEMA public FROM dataforge_telemetry_ingest"
    )
