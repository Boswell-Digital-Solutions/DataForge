from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from fastapi import HTTPException
from app.models import models, schemas
from app.utils.embeddings import chunk_text, generate_embeddings_batch
from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.utils.cache_governance import build_doc_cache_key, delete_cache_key_sync
from app.utils.corpus_versioning import bump_corpus_version_sync, get_sync_redis_client

logger = logging.getLogger(__name__)


def _invalidate_document_cache(document_id: int, event: str) -> None:
    redis_client = get_sync_redis_client()
    if redis_client is None:
        return
    delete_cache_key_sync(
        redis_client,
        build_doc_cache_key(document_id),
        event=event,
        log=logger,
    )

# ============================================
# Domain CRUD
# ============================================

def create_domain(db: Session, domain: schemas.DomainCreate):
    db_domain = models.Domain(**domain.model_dump())
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    return db_domain

def get_domain(db: Session, domain_id: str):
    return db.query(models.Domain).filter(models.Domain.id == domain_id).first()

def get_domains(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Domain).offset(skip).limit(limit).all()

def delete_domain(db: Session, domain_id: str):
    domain = get_domain(db, domain_id)
    if domain:
        db.delete(domain)
        db.commit()
        return True
    return False

# ============================================
# Tag CRUD
# ============================================

def get_or_create_tag(db: Session, tag_name: str):
    tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
    if not tag:
        tag = models.Tag(name=tag_name)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    return tag

def get_tags(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tag).offset(skip).limit(limit).all()

# ============================================
# Document CRUD
# ============================================

async def create_document(db: Session, document: schemas.DocumentCreate):
    """
    Create a document with automatic chunking and embedding generation.
    """
    try:
        # Create document
        db_document = models.Document(
            domain_id=document.domain_id,
            title=document.title,
            doc_type=document.doc_type,
            content=document.content,
            doc_metadata=document.doc_metadata,  # Fixed field name
            is_published=document.is_published
        )

        # Add tags
        if document.tags:
            for tag_name in document.tags:
                tag = get_or_create_tag(db, tag_name)
                db_document.tags.append(tag)

        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        bump_corpus_version_sync(db, "doc_insert", db_document.id)

        # Chunk the content
        chunks = chunk_text(document.content, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        logger.info(f"Chunking document '{document.title}' into {len(chunks)} chunks")

        # Generate embeddings for all chunks
        embeddings = await generate_embeddings_batch(chunks)

        # Create chunk records
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = models.Chunk(
                document_id=db_document.id,
                content=chunk_text,
                chunk_index=idx,
                embedding=embedding
            )
            db.add(db_chunk)

        db.commit()
        db.refresh(db_document)
        bump_corpus_version_sync(db, "chunk_insert", db_document.id)

        logger.info(f"Successfully created document '{document.title}' with {len(chunks)} chunks")
        return db_document

    except Exception as e:
        logger.error(f"Failed to create document: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create document: {str(e)}"
        )

def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_documents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    domain_id: Optional[str] = None,
    is_published: Optional[bool] = None
):
    query = db.query(models.Document)

    if domain_id:
        query = query.filter(models.Document.domain_id == domain_id)
    if is_published is not None:
        query = query.filter(models.Document.is_published == is_published)

    return query.offset(skip).limit(limit).all()

async def update_document(db: Session, document_id: int, document_update: schemas.DocumentUpdate):
    """
    Update a document. If content is updated, re-chunk and re-embed.
    """
    try:
        db_document = get_document(db, document_id)
        if not db_document:
            return None

        update_data = document_update.model_dump(exclude_unset=True)

        # Handle tags separately
        if "tags" in update_data:
            tag_names = update_data.pop("tags")
            db_document.tags.clear()
            for tag_name in tag_names:
                tag = get_or_create_tag(db, tag_name)
                db_document.tags.append(tag)

        # Check if content changed
        content_changed = "content" in update_data and update_data["content"] != db_document.content
        _invalidate_document_cache(document_id, "document_update")

        # Update other fields
        for key, value in update_data.items():
            setattr(db_document, key, value)

        # If content changed, re-chunk and re-embed
        if content_changed:
            logger.info(f"Content changed for document {document_id}, re-chunking and re-embedding")

            # Delete old chunks
            db.query(models.Chunk).filter(models.Chunk.document_id == document_id).delete()

            # Create new chunks
            chunks = chunk_text(db_document.content, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
            embeddings = await generate_embeddings_batch(chunks)

            for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                db_chunk = models.Chunk(
                    document_id=db_document.id,
                    content=chunk_text,
                    chunk_index=idx,
                    embedding=embedding
                )
                db.add(db_chunk)

            logger.info(f"Re-chunked document {document_id} into {len(chunks)} chunks")

        db.commit()
        db.refresh(db_document)
        if content_changed:
            bump_corpus_version_sync(db, "reindex", document_id)
        return db_document

    except Exception as e:
        logger.error(f"Failed to update document {document_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update document: {str(e)}"
        )

def delete_document(db: Session, document_id: int):
    document = get_document(db, document_id)
    if document:
        db.delete(document)
        db.commit()
        _invalidate_document_cache(document_id, "document_delete")
        bump_corpus_version_sync(db, "doc_delete", document_id)
        return True
    return False

# ============================================
# Stats
# ============================================

def get_stats(db: Session):
    return schemas.Stats(
        total_documents=db.query(models.Document).count(),
        total_chunks=db.query(models.Chunk).count(),
        total_domains=db.query(models.Domain).count(),
        total_tags=db.query(models.Tag).count()
    )
