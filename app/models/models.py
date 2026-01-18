from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Table, Float, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from pgvector.sqlalchemy import Vector
from app.database import Base

# Association table for document-tag many-to-many relationship
document_tags = Table(
    'document_tags',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Domain(Base):
    __tablename__ = "domains"

    id = Column(String(100), primary_key=True)  # e.g., "writing_craft"
    label = Column(String(255), nullable=False)  # e.g., "Writing Craft"
    description = Column(Text)
    parent_id = Column(String(100), ForeignKey('domains.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    parent = relationship("Domain", remote_side=[id], backref="children")
    documents = relationship("Document", back_populates="domain", cascade="all, delete-orphan")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    documents = relationship("Document", secondary=document_tags, back_populates="tags")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(String(100), ForeignKey('domains.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    doc_type = Column(String(50), nullable=False, index=True)  # guide, pattern, example, reference
    content = Column(Text, nullable=False)
    doc_metadata = Column(Text)  # JSON string for flexible metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    is_published = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=document_tags, back_populates="documents")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    embedding = Column(Vector(1536))  # OpenAI ada-002 dimension (adjust for other providers)
    search_vector = Column(TSVECTOR)  # Full-text search vector (automatically maintained by trigger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")


# =============================================================================
# ForgeAgents Execution Persistence (Phase 2)
# =============================================================================

class ExecutionIndex(Base):
    """Denormalized index for fast /history queries.

    Stores key fields from RunEvidence.v1 for efficient filtering and sorting
    without needing to parse JSONB. Uses CHECK constraints to enforce vocabulary
    at the database level (belt-and-suspenders with Python validation).
    """
    __tablename__ = "execution_index"

    # Primary identifiers
    run_id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    workflow_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)

    # Repository context
    repo_id = Column(String(255), nullable=False, index=True)
    repo_sha = Column(String(64), nullable=False)
    branch = Column(String(255), nullable=False, index=True)

    # Execution mode
    mode = Column(String(20), nullable=False)  # batch, interactive, etc.
    invoker = Column(String(100), nullable=True)

    # Normalized terminal status (4 values only)
    final_status = Column(String(20), nullable=False, index=True)

    # Conditional metadata (vocabulary-constrained)
    fail_reason = Column(String(30), nullable=True)  # Only when final_status == 'fail'
    abort_kind = Column(String(10), nullable=True)   # Only when final_status == 'aborted'
    abort_reason = Column(String(30), nullable=True) # Only when final_status == 'aborted'

    # Quality metrics
    promotion_ready = Column(Boolean, default=False, index=True)
    confidence_floor = Column(Float, default=0.0)

    # Evidence references
    evidence_hash = Column(String(71), nullable=True)  # sha256:... (71 chars)
    artifact_bundle_pointer = Column(String(1024), nullable=True)

    # Timing
    total_duration_ms = Column(Integer, nullable=True)
    node_count = Column(Integer, nullable=True)
    attempt_count = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Extensible metadata (JSON for highest_risk_flags, notes, etc.)
    # Note: 'metadata' is reserved by SQLAlchemy, so we use 'run_metadata' as attribute name
    # but map to 'metadata' column in DB
    run_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    evidence = relationship("RunEvidence", back_populates="index", uselist=False, cascade="all, delete-orphan")

    # Note: CHECK constraints are defined in Alembic migration for better control
    # The Python layer (ForgeAgents) validates before write; DB is belt-and-suspenders

    __table_args__ = (
        # Composite indexes for common query patterns
        # Index('ix_execution_index_repo_branch', 'repo_id', 'branch'),  # Defined in migration
        # Index('ix_execution_index_workflow_status', 'workflow_id', 'final_status'),
        # Index('ix_execution_index_session_created', 'session_id', 'created_at'),
    )


class RunEvidence(Base):
    """Full RunEvidence.v1 document storage.

    Stores complete evidence as JSONB for detailed queries and auditing.
    The execution_index table provides fast indexed access; this table
    provides the full document when needed.
    """
    __tablename__ = "run_evidence"

    # Primary key (FK to execution_index)
    run_id = Column(String(64), ForeignKey('execution_index.run_id', ondelete='CASCADE'), primary_key=True)

    # Version tracking
    evidence_version = Column(String(20), nullable=False, default="RunEvidence.v1")

    # Content hash for integrity verification
    evidence_hash = Column(String(71), nullable=False)  # sha256:...

    # Full evidence document
    evidence = Column(JSONB, nullable=False)

    # Write timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    index = relationship("ExecutionIndex", back_populates="evidence")
