"""
CRUD operations for private_source_profiles table.

All queries are scoped by workspace_id for multi-tenant isolation (A-001).
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.private_source_models import PrivateSourceProfile
from app.models.private_source_schemas import PSPCreate, PSPUpdate


def create_profile(db: Session, data: PSPCreate) -> PrivateSourceProfile:
    """Create a new private source profile."""
    row = PrivateSourceProfile(
        workspace_id=data.workspace_id,
        name=data.name,
        description=data.description,
        source_type=data.source_type,
        base_url=data.base_url,
        allowed_paths=data.allowed_paths,
        auth_type=data.auth_type,
        config=data.config,
        quality_gates=data.quality_gates,
        is_active=data.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_profile(db: Session, profile_id: int) -> Optional[PrivateSourceProfile]:
    """Get a single profile by ID."""
    return (
        db.query(PrivateSourceProfile)
        .filter(PrivateSourceProfile.id == profile_id)
        .first()
    )


def list_profiles(
    db: Session,
    *,
    workspace_id: str,
    source_type: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PrivateSourceProfile], int]:
    """List profiles scoped by workspace_id."""
    query = db.query(PrivateSourceProfile).filter(
        PrivateSourceProfile.workspace_id == workspace_id
    )
    if active_only:
        query = query.filter(PrivateSourceProfile.is_active.is_(True))
    if source_type:
        query = query.filter(PrivateSourceProfile.source_type == source_type)
    total = query.count()
    items = (
        query.order_by(PrivateSourceProfile.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def update_profile(
    db: Session, profile_id: int, data: PSPUpdate
) -> Optional[PrivateSourceProfile]:
    """Update an existing profile (partial update)."""
    row = (
        db.query(PrivateSourceProfile)
        .filter(PrivateSourceProfile.id == profile_id)
        .first()
    )
    if not row:
        return None
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_profile(db: Session, profile_id: int) -> bool:
    """Delete a profile by ID."""
    row = (
        db.query(PrivateSourceProfile)
        .filter(PrivateSourceProfile.id == profile_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
