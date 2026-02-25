"""SQLAlchemy ORM model for compression dictionaries."""

from sqlalchemy import Column, Integer, String, Float, DateTime, LargeBinary, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.database import Base


class CompressionDictionary(Base):
    """Zstandard compression dictionary stored in DataForge."""

    __tablename__ = "compression_dictionaries"

    dictionary_id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    service_pair = Column(String(100), nullable=False, index=True)
    payload_class = Column(String(100), nullable=False)
    schema_version_min = Column(String(20), nullable=True)
    schema_version_max = Column(String(20), nullable=True)
    algorithm = Column(String(20), nullable=False, default="zstd")
    dictionary_size_bytes = Column(Integer, nullable=False)
    dictionary_blob = Column(LargeBinary, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    training_sample_n = Column(Integer, nullable=False)
    training_params = Column(JSONB, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    program = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="TRAINING", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    retired_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('TRAINING', 'CANDIDATE', 'ACTIVE', 'RETIRED')",
            name="ck_compression_dict_status",
        ),
        CheckConstraint(
            "program IN ('transport', 'archive')",
            name="ck_compression_dict_program",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CompressionDictionary(id={self.dictionary_id}, "
            f"name={self.name!r}, service_pair={self.service_pair!r}, "
            f"status={self.status!r})>"
        )
