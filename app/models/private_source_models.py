"""
Private Source Profile models for PSIM (Private Source Ingestion Missions).

Tables:
  - private_source_profiles: Operator-curated source configurations for
    authenticated crawling via ForgeCommand as Root of Trust.

Each PSP defines a crawl scope (base_url + allowed_paths), authentication
method, and quality gate overrides. Secrets live in the OS keyring via
ForgeCommand; only profile metadata is stored here.

Amendment references:
  - A-001: workspace_id for multi-tenant isolation
  - A-004: Keyring abstraction (OS keyring via `keyring` crate, not GNOME-specific)
  - A-006: quality_gates override Rake's CLEAN stage defaults when non-null
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class PrivateSourceProfile(Base):
    """Operator-curated private source configuration.

    Stores crawl scope, auth method, and quality overrides. Credentials
    are stored in the OS keyring via ForgeCommand — never in this table.
    """
    __tablename__ = "private_source_profiles"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Source configuration
    source_type = Column(String(50), nullable=False, default="web")
    base_url = Column(String(2048), nullable=False)
    allowed_paths = Column(JSONB, nullable=False, default=list)
    auth_type = Column(String(50), nullable=False, default="cookie")

    # Flexible config (PrivateSourceConfig JSON)
    config = Column(JSONB, nullable=False, default=dict)

    # Quality gate overrides (A-006): null fields use Rake defaults
    quality_gates = Column(JSONB, nullable=True)

    # Lifecycle
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index('ix_psp_workspace_active', 'workspace_id', 'is_active'),
        Index('ix_psp_workspace_name', 'workspace_id', 'name', unique=True),
        CheckConstraint(
            "auth_type IN ('cookie', 'bearer', 'basic', 'header')",
            name="ck_psp_auth_type",
        ),
        CheckConstraint(
            "source_type IN ('web', 'api', 'rss')",
            name="ck_psp_source_type",
        ),
    )

    def __repr__(self):
        return (
            f"<PrivateSourceProfile(id={self.id}, "
            f"name='{self.name}', "
            f"workspace_id='{self.workspace_id}')>"
        )
