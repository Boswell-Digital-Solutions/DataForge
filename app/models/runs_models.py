"""
DataForge - Run History Models

SQLAlchemy models for storing prompt execution runs and their results.
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Run(Base):
    """
    Prompt execution run from VibeForge/NeuroForge.
    
    Stores complete execution details including prompt snapshot,
    context used, token usage, costs, and timing information.
    """
    __tablename__ = "runs"

    # Primary identification
    run_id = Column(String(255), primary_key=True, index=True)
    workspace_id = Column(String(255), nullable=False, index=True)
    
    # Prompt details
    prompt_snapshot = Column(Text, nullable=False)
    context_block_ids = Column(JSON, default=list)  # List of context block IDs used
    
    # Execution metrics
    total_latency_ms = Column(Float, nullable=False)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    tags = Column(JSON, default=list)  # User-defined tags
    notes = Column(Text, nullable=True)  # User notes about this run
    status = Column(String(50), nullable=False, default="success", index=True)  # success, error, partial
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    results = relationship(
        "ModelResult",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="joined"  # Eager load results with run
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_workspace_created', 'workspace_id', 'created_at'),
        Index('idx_workspace_status', 'workspace_id', 'status'),
        Index('idx_created_status', 'created_at', 'status'),
    )
    
    def __repr__(self):
        return f"<Run(run_id={self.run_id}, workspace={self.workspace_id}, tokens={self.total_tokens})>"


class ModelResult(Base):
    """
    Result from a single model execution within a run.
    
    A run can have multiple results if executed against multiple models.
    Stores model-specific output, token usage, and timing.
    """
    __tablename__ = "model_results"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(
        String(255),
        ForeignKey('runs.run_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Model identification
    model_id = Column(String(255), nullable=False, index=True)  # e.g., "claude-3.5-sonnet"
    provider = Column(String(100), nullable=False, index=True)  # e.g., "anthropic", "openai", "ollama"
    
    # Output
    output = Column(Text, nullable=False)
    
    # Token usage
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Cost (calculated from tokens and pricing)
    cost_usd = Column(Float, nullable=False, default=0.0)
    
    # Execution metrics
    latency_ms = Column(Float, nullable=False)
    
    # Status
    status = Column(String(50), nullable=False, default="success")  # success, error
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    run = relationship("Run", back_populates="results")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_run_model', 'run_id', 'model_id'),
        Index('idx_provider_model', 'provider', 'model_id'),
        Index('idx_model_created', 'model_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ModelResult(id={self.id}, model={self.model_id}, tokens={self.total_tokens})>"


# ============================================================================
# Notes on TimescaleDB Integration
# ============================================================================
#
# For production deployments with high run volumes, consider converting
# the 'runs' table to a TimescaleDB hypertable for better time-series performance:
#
# 1. Install TimescaleDB extension:
#    CREATE EXTENSION IF NOT EXISTS timescaledb;
#
# 2. Convert runs table to hypertable:
#    SELECT create_hypertable('runs', 'created_at', if_not_exists => TRUE);
#
# 3. Create compression policy (optional, for older data):
#    ALTER TABLE runs SET (
#      timescaledb.compress,
#      timescaledb.compress_segmentby = 'workspace_id'
#    );
#    
#    SELECT add_compression_policy('runs', INTERVAL '7 days');
#
# 4. Create retention policy (optional, to auto-delete old runs):
#    SELECT add_retention_policy('runs', INTERVAL '90 days');
#
# Benefits:
# - Faster time-range queries
# - Automatic data partitioning by time
# - Better compression for historical data
# - Efficient aggregations over time periods
#
# ============================================================================
