"""add map cartographer tables (settings, viewports, exports)

Revision ID: map_carto_001
Revises: collab_001
Create Date: 2026-02-18

Adds map_settings, map_viewports, map_exports tables.
Previously managed by AuthorForge API local migrations 004, 005, 006.
Now owned by DataForge Alembic (A2: escaped table migration).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'map_carto_001'
down_revision: Union[str, Sequence[str], None] = 'collab_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # map_settings: one row per project (project_id is the PK)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS map_settings (
            project_id      INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            canvas_width    INTEGER NOT NULL DEFAULT 640,
            canvas_height   INTEGER NOT NULL DEFAULT 400,
            scale_km_per_unit REAL NOT NULL DEFAULT 2.5,
            grid_enabled    BOOLEAN NOT NULL DEFAULT false,
            grid_size       INTEGER NOT NULL DEFAULT 20,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # map_viewports: saved viewport presets for export
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS map_viewports (
            id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name            TEXT NOT NULL DEFAULT 'Full Map',
            crop_x          REAL NOT NULL DEFAULT 0,
            crop_y          REAL NOT NULL DEFAULT 0,
            crop_w          REAL NOT NULL DEFAULT 640,
            crop_h          REAL NOT NULL DEFAULT 400,
            output_width    INTEGER NOT NULL DEFAULT 1920,
            output_height   INTEGER NOT NULL DEFAULT 1200,
            dpi             INTEGER NOT NULL DEFAULT 150,
            show_labels     BOOLEAN NOT NULL DEFAULT true,
            show_roads      BOOLEAN NOT NULL DEFAULT true,
            show_pins       BOOLEAN NOT NULL DEFAULT true,
            show_grid       BOOLEAN NOT NULL DEFAULT false,
            show_compass    BOOLEAN NOT NULL DEFAULT true,
            is_default      BOOLEAN NOT NULL DEFAULT false,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_map_viewports_project ON map_viewports(project_id)"
    ))

    # map_exports: export job history
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS map_exports (
            id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            viewport_id     TEXT REFERENCES map_viewports(id) ON DELETE SET NULL,
            name            TEXT NOT NULL DEFAULT 'Untitled Export',
            format          TEXT NOT NULL DEFAULT 'png'
                              CHECK (format IN ('png', 'svg', 'jpg')),
            dpi             INTEGER NOT NULL DEFAULT 150,
            width_px        INTEGER,
            height_px       INTEGER,
            file_size       BIGINT,
            svg_hash        TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_map_exports_project ON map_exports(project_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_map_exports_viewport ON map_exports(viewport_id)"
    ))


def downgrade() -> None:
    op.drop_table('map_exports')
    op.drop_index('idx_map_viewports_project', table_name='map_viewports')
    op.drop_table('map_viewports')
    op.drop_table('map_settings')
