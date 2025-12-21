"""
Unit tests for database models.
"""
import pytest
from app.models import models


@pytest.mark.unit
class TestDomainModel:
    """Test Domain model."""
    
    def test_create_domain(self, db):
        """Test creating a domain."""
        domain = models.Domain(
            id="writing_craft",
            label="Writing Craft",
            description="Writing techniques and best practices"
        )
        db.add(domain)
        db.commit()
        db.refresh(domain)
        
        assert domain.id == "writing_craft"
        assert domain.label == "Writing Craft"
        assert domain.created_at is not None
    
    def test_domain_hierarchy(self, db):
        """Test parent-child domain relationships."""
        parent = models.Domain(
            id="parent",
            label="Parent Domain"
        )
        db.add(parent)
        db.commit()
        
        child = models.Domain(
            id="child",
            label="Child Domain",
            parent_id="parent"
        )
        db.add(child)
        db.commit()
        db.refresh(child)
        
        assert child.parent_id == "parent"
        assert child.parent.id == "parent"
    
    def test_domain_cascade_delete(self, db, test_domain):
        """Test that deleting domain cascades to documents."""
        document = models.Document(
            domain_id=test_domain.id,
            title="Test Doc",
            doc_type="guide",
            content="Test content"
        )
        db.add(document)
        db.commit()
        
        # Delete domain
        db.delete(test_domain)
        db.commit()
        
        # Document should be deleted too
        doc = db.query(models.Document).filter_by(title="Test Doc").first()
        assert doc is None


@pytest.mark.unit
class TestTagModel:
    """Test Tag model."""
    
    def test_create_tag(self, db):
        """Test creating a tag."""
        tag = models.Tag(name="character-development")
        db.add(tag)
        db.commit()
        db.refresh(tag)
        
        assert tag.id is not None
        assert tag.name == "character-development"
        assert tag.created_at is not None
    
    def test_tag_unique_name(self, db, test_tag):
        """Test that tag names must be unique."""
        duplicate_tag = models.Tag(name="test-tag")
        db.add(duplicate_tag)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()


@pytest.mark.unit
class TestDocumentModel:
    """Test Document model."""
    
    def test_create_document(self, db, test_domain):
        """Test creating a document."""
        doc = models.Document(
            domain_id=test_domain.id,
            title="Test Document",
            doc_type="guide",
            content="This is test content",
            is_published=True
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        assert doc.id is not None
        assert doc.title == "Test Document"
        assert doc.domain_id == test_domain.id
        assert doc.is_published is True
        assert doc.created_at is not None
    
    def test_document_with_tags(self, db, test_domain, test_tag):
        """Test document with tags relationship."""
        doc = models.Document(
            domain_id=test_domain.id,
            title="Tagged Document",
            doc_type="guide",
            content="Content"
        )
        doc.tags.append(test_tag)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        assert len(doc.tags) == 1
        assert doc.tags[0].name == "test-tag"
    
    def test_document_metadata(self, db, test_domain):
        """Test document metadata field."""
        doc = models.Document(
            domain_id=test_domain.id,
            title="Doc with Metadata",
            doc_type="guide",
            content="Content",
            doc_metadata='{"author": "Test Author", "version": "1.0"}'
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        assert doc.doc_metadata is not None
        assert "author" in doc.doc_metadata


@pytest.mark.unit
class TestChunkModel:
    """Test Chunk model."""
    
    def test_create_chunk(self, db, test_domain, mock_embedding):
        """Test creating a chunk with embedding."""
        doc = models.Document(
            domain_id=test_domain.id,
            title="Test Doc",
            doc_type="guide",
            content="Content"
        )
        db.add(doc)
        db.commit()
        
        chunk = models.Chunk(
            document_id=doc.id,
            content="This is a chunk of text",
            chunk_index=0,
            embedding=mock_embedding
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.document_id == doc.id
        assert chunk.chunk_index == 0
        assert chunk.embedding is not None
    
    def test_chunk_cascade_delete(self, db, test_domain, mock_embedding):
        """Test that deleting document cascades to chunks."""
        doc = models.Document(
            domain_id=test_domain.id,
            title="Test Doc",
            doc_type="guide",
            content="Content"
        )
        db.add(doc)
        db.commit()
        
        chunk = models.Chunk(
            document_id=doc.id,
            content="Chunk",
            chunk_index=0,
            embedding=mock_embedding
        )
        db.add(chunk)
        db.commit()
        chunk_id = chunk.id
        
        # Delete document
        db.delete(doc)
        db.commit()
        
        # Chunk should be deleted
        deleted_chunk = db.query(models.Chunk).filter_by(id=chunk_id).first()
        assert deleted_chunk is None

