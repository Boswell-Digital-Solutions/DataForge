"""Durable relational records for NeuroForge cloud-image control state."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


class CloudImageJob(Base):
    __tablename__ = "cloud_image_jobs"

    job_id = Column(String(96), primary_key=True)
    request_id = Column(String(96), nullable=False, unique=True, index=True)
    caller_identity = Column(String(256), nullable=False, index=True)
    idempotency_key = Column(String(256), nullable=False)
    correlation_id = Column(String(256), nullable=False, index=True)
    source_service = Column(String(128), nullable=False)
    app_id = Column(String(64), nullable=False, index=True)
    use_case = Column(String(96), nullable=False)
    status = Column(String(64), nullable=False, index=True)
    provider_override = Column(String(64), nullable=True)
    policy_block_code = Column(String(128), nullable=True)
    requested_count = Column(Integer, nullable=False)
    accepted_final_count = Column(Integer, nullable=False, default=0)
    candidate_count = Column(Integer, nullable=False, default=0)
    replacement_round = Column(Integer, nullable=False, default=0)
    max_replacement_rounds = Column(Integer, nullable=False)
    max_total_candidates = Column(Integer, nullable=False)
    max_cost_usd = Column(Numeric(12, 4), nullable=False)
    fulfillment_limits_exhausted = Column(Boolean, nullable=False, default=False)
    deadline_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    terminal_at = Column(DateTime(timezone=True), nullable=True)
    row_version = Column(Integer, nullable=False, default=1)
    record_payload = Column(JSON, nullable=False)


class CloudImageProtectedRequest(Base):
    __tablename__ = "cloud_image_protected_requests"

    job_id = Column(
        String(96),
        ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
        primary_key=True,
    )
    schema_version = Column(String(128), nullable=False)
    algorithm = Column(String(32), nullable=False)
    key_ref = Column(String(256), nullable=False)
    nonce_b64 = Column(String(64), nullable=False)
    aad_b64 = Column(String(512), nullable=False)
    ciphertext = Column(Text, nullable=False)
    ciphertext_sha256 = Column(String(71), nullable=False)
    semantic_request_fingerprint = Column(String(76), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    retention_until = Column(DateTime(timezone=True), nullable=False)


class CloudImageIdempotencyBinding(Base):
    __tablename__ = "cloud_image_idempotency_bindings"
    __table_args__ = (
        UniqueConstraint(
            "caller_identity",
            "idempotency_key",
            name="uq_cloud_image_idempotency_scope",
        ),
    )

    binding_id = Column(String(96), primary_key=True)
    caller_identity = Column(String(256), nullable=False)
    idempotency_key = Column(String(256), nullable=False)
    semantic_request_fingerprint = Column(String(76), nullable=False)
    job_id = Column(
        String(96),
        ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False)


class CloudImageOperationReceipt(Base):
    __tablename__ = "cloud_image_operation_receipts"

    operation_id = Column(String(128), primary_key=True)
    operation_kind = Column(String(32), nullable=False)
    operation_fingerprint = Column(String(76), nullable=False)
    job_id = Column(
        String(96),
        ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resulting_row_version = Column(Integer, nullable=False)
    resulting_status = Column(String(64), nullable=False)
    resulting_record_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class CloudImageEvent(Base):
    __tablename__ = "cloud_image_events"

    event_id = Column(String(96), primary_key=True)
    event_type = Column(String(128), nullable=False, index=True)
    caller_identity = Column(String(256), nullable=False)
    app_id = Column(String(64), nullable=False)
    correlation_id = Column(String(256), nullable=False, index=True)
    job_id = Column(
        String(96),
        ForeignKey("cloud_image_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class CloudImageOutbox(Base):
    __tablename__ = "cloud_image_outbox"

    outbox_id = Column(String(96), primary_key=True)
    event_id = Column(
        String(96),
        ForeignKey("cloud_image_events.event_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    aggregate_id = Column(String(96), nullable=False, index=True)
    event_type = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    delivery_attempts = Column(Integer, nullable=False, default=0)
