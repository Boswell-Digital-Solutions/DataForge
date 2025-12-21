"""
Integration tests for CRUD operations.
"""
import pytest
from sqlalchemy.orm import Session
from app.api import crud
from app.models import models, schemas


@pytest.mark.integration
class TestDomainCRUD:
    """Test domain CRUD operations."""
    
    def test_create_and_get_domain(self, db: Session):
        """Test creating and retrieving a domain."""
        domain_data = schemas.DomainCreate(
            id="test_crud",
            label="Test CRUD Domain",
            description="Testing CRUD operations"
        )
        
        created = crud.create_domain(db, domain_data)
        assert created.id == "test_crud"
        
        retrieved = crud.get_domain(db, "test_crud")
        assert retrieved is not None
        assert retrieved.label == "Test CRUD Domain"
    
    def test_list_domains(self, db: Session, test_domain):
        """Test listing all domains."""
        domains = crud.get_domains(db)

        assert len(domains) >= 1
        assert any(d.id == test_domain.id for d in domains)
    
    def test_create_domain_with_parent(self, db: Session, test_domain):
        """Test creating domain with parent relationship."""
        child_data = schemas.DomainCreate(
            id="child_domain",
            label="Child Domain",
            parent_id=test_domain.id
        )
        
        child = crud.create_domain(db, child_data)
        assert child.parent_id == test_domain.id
        assert child.parent.id == test_domain.id


@pytest.mark.integration
class TestDocumentCRUD:
    """Test document CRUD operations."""
    
    def test_list_documents(self, db: Session):
        """Test listing documents."""
        docs = crud.get_documents(db)
        assert isinstance(docs, list)

    def test_list_documents_by_domain(self, db: Session, test_domain):
        """Test filtering documents by domain."""
        # Create a document
        doc = models.Document(
            domain_id=test_domain.id,
            title="Test Doc",
            doc_type="guide",
            content="Test content"
        )
        db.add(doc)
        db.commit()

        # List by domain
        docs = crud.get_documents(db, domain_id=test_domain.id)
        assert len(docs) >= 1
        assert all(d.domain_id == test_domain.id for d in docs)

    def test_list_published_documents(self, db: Session, test_domain):
        """Test filtering by published status."""
        # Create published doc
        pub_doc = models.Document(
            domain_id=test_domain.id,
            title="Published",
            doc_type="guide",
            content="Content",
            is_published=True
        )
        db.add(pub_doc)

        # Create unpublished doc
        unpub_doc = models.Document(
            domain_id=test_domain.id,
            title="Unpublished",
            doc_type="guide",
            content="Content",
            is_published=False
        )
        db.add(unpub_doc)
        db.commit()

        # List only published
        docs = crud.get_documents(db, is_published=True)
        assert all(d.is_published for d in docs)


@pytest.mark.integration
class TestTagCRUD:
    """Test tag CRUD operations."""
    
    def test_list_tags(self, db: Session, test_tag):
        """Test listing tags."""
        tags = crud.get_tags(db)

        assert len(tags) >= 1
        assert any(t.name == test_tag.name for t in tags)
    
    def test_get_or_create_tag_existing(self, db: Session, test_tag):
        """Test getting existing tag."""
        tag = crud.get_or_create_tag(db, test_tag.name)
        
        assert tag.id == test_tag.id
        assert tag.name == test_tag.name
    
    def test_get_or_create_tag_new(self, db: Session):
        """Test creating new tag."""
        tag = crud.get_or_create_tag(db, "new-tag")
        
        assert tag.id is not None
        assert tag.name == "new-tag"


@pytest.mark.integration
class TestStatistics:
    """Test statistics gathering."""
    
    def test_get_stats(self, db: Session, test_domain, test_tag):
        """Test getting statistics."""
        stats = crud.get_stats(db)
        
        assert stats.total_domains >= 1
        assert stats.total_tags >= 1
        assert stats.total_documents >= 0
        assert stats.total_chunks >= 0
    
    def test_stats_with_documents(self, db: Session, test_domain):
        """Test stats with documents."""
        # Create a document
        doc = models.Document(
            domain_id=test_domain.id,
            title="Test",
            doc_type="guide",
            content="Content"
        )
        db.add(doc)
        db.commit()
        
        stats = crud.get_stats(db)
        assert stats.total_documents >= 1

