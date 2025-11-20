"""DataForge API router (stub)."""

from fastapi import APIRouter, HTTPException
from typing import List
from app.models import DocumentModel, CorpusModel, SearchResultModel

router = APIRouter(prefix="/v1/dataforge", tags=["DataForge"])


@router.post("/corpus", response_model=CorpusModel, status_code=201)
async def create_corpus(name: str):
    """Create a new corpus for document ingestion."""
    return CorpusModel(id="corpus-stub", name=name, document_count=0, created_at="2025-11-18T00:00:00Z")


@router.post("/corpus/{corpus_id}/ingest", status_code=202)
async def ingest_document(corpus_id: str, document: DocumentModel):
    """Ingest a document into a corpus."""
    return {"status": "queued", "corpus_id": corpus_id, "document_id": document.id}


@router.get("/corpus/{corpus_id}/search", response_model=List[SearchResultModel])
async def search_corpus(corpus_id: str, query: str):
    """Search a corpus (vector semantic search stub)."""
    return []  # TODO: Implement with vector store


@router.get("/corpus/{corpus_id}/documents", response_model=List[DocumentModel])
async def list_documents(corpus_id: str):
    """List documents in a corpus."""
    return []
