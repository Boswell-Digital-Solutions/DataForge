from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import models, schemas
from app.utils.auth import get_current_admin_user
from app.api import crud

router = APIRouter(prefix="/admin", tags=["admin"])

# ============================================
# Domains
# ============================================

@router.post("/domains", response_model=schemas.Domain)
def create_domain(
    domain: schemas.DomainCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Create a new domain (admin only)"""
    existing = crud.get_domain(db, domain.id)
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
    return crud.create_domain(db, domain)

@router.get("/domains", response_model=List[schemas.Domain])
def list_domains(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List all domains (admin only)"""
    return crud.get_domains(db, skip=skip, limit=limit)

@router.get("/domains/{domain_id}", response_model=schemas.Domain)
def get_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get a specific domain (admin only)"""
    domain = crud.get_domain(db, domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain

@router.delete("/domains/{domain_id}")
def delete_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a domain (admin only)"""
    if not crud.delete_domain(db, domain_id):
        raise HTTPException(status_code=404, detail="Domain not found")
    return {"message": "Domain deleted successfully"}

# ============================================
# Documents
# ============================================

@router.post("/documents", response_model=schemas.Document)
async def create_document(
    document: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Create a new document with automatic chunking and embedding (admin only).

    The document will be automatically:
    - Chunked into semantic units
    - Embedded using the configured provider
    - Made searchable via the public search API
    """
    # Verify domain exists
    domain = crud.get_domain(db, document.domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    return await crud.create_document(db, document)

@router.get("/documents", response_model=List[schemas.Document])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    domain_id: Optional[str] = None,
    is_published: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List documents with optional filters (admin only)"""
    return crud.get_documents(
        db,
        skip=skip,
        limit=limit,
        domain_id=domain_id,
        is_published=is_published
    )

@router.get("/documents/{document_id}", response_model=schemas.Document)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get a specific document (admin only)"""
    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.patch("/documents/{document_id}", response_model=schemas.Document)
async def update_document(
    document_id: int,
    document_update: schemas.DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Update a document (admin only).

    If content is updated, the document will be automatically re-chunked and re-embedded.
    """
    document = await crud.update_document(db, document_id, document_update)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a document (admin only)"""
    if not crud.delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

# ============================================
# Tags
# ============================================

@router.get("/tags", response_model=List[schemas.Tag])
def list_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List all tags (admin only)"""
    return crud.get_tags(db, skip=skip, limit=limit)
