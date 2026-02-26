"""
Private Source Profile API — CRUD for operator-curated source configurations.

Endpoints:
  - POST   /api/v1/private-source-profiles               — Create profile
  - GET    /api/v1/private-source-profiles/{id}           — Get profile by ID
  - GET    /api/v1/private-source-profiles                — List profiles (workspace scoped)
  - PUT    /api/v1/private-source-profiles/{id}           — Update profile
  - DELETE /api/v1/private-source-profiles/{id}           — Delete profile
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.api import private_source_crud as crud
from app.models.private_source_schemas import (
    PSPCreate, PSPUpdate, PSPResponse, PSPListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/private-source-profiles",
    tags=["PrivateSourceProfiles"],
)


@router.post("", status_code=201, response_model=PSPResponse)
def create_profile(data: PSPCreate, db: Session = Depends(get_db)):
    """Create a new private source profile."""
    # Check for duplicate name within workspace
    existing, _ = crud.list_profiles(
        db, workspace_id=data.workspace_id, active_only=False, limit=1, offset=0
    )
    for p in existing:
        if p.name == data.name:
            raise HTTPException(
                status_code=409,
                detail=f"Profile '{data.name}' already exists in workspace"
            )

    row = crud.create_profile(db, data)
    logger.info(
        "private_source_profile_created",
        extra={"profile_id": row.id, "workspace_id": data.workspace_id, "name": data.name}
    )
    return PSPResponse.model_validate(row)


@router.get("/{profile_id}", response_model=PSPResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get a single private source profile by ID."""
    row = crud.get_profile(db, profile_id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return PSPResponse.model_validate(row)


@router.get("", response_model=PSPListResponse)
def list_profiles(
    workspace_id: str = Query(..., description="Required workspace scope"),
    source_type: str | None = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List private source profiles for a workspace."""
    items, total = crud.list_profiles(
        db,
        workspace_id=workspace_id,
        source_type=source_type,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return PSPListResponse(
        items=[PSPResponse.model_validate(row) for row in items],
        total=total,
    )


@router.put("/{profile_id}", response_model=PSPResponse)
def update_profile(
    profile_id: int,
    data: PSPUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing private source profile."""
    row = crud.update_profile(db, profile_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    logger.info(
        "private_source_profile_updated",
        extra={"profile_id": profile_id}
    )
    return PSPResponse.model_validate(row)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    """Delete a private source profile."""
    deleted = crud.delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    logger.info(
        "private_source_profile_deleted",
        extra={"profile_id": profile_id}
    )
