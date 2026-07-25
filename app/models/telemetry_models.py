"""ORM mappings for canonical Forge telemetry durable storage."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ForgeEventV1Record(Base):
    """Durable canonical Forge telemetry event owned by DataForge.

    Alembic owns the PostgreSQL checks, expression indexes, and atomic identity
    function. This mapping intentionally has no alias or
    relationship to the physically retained pre-v1 ``events`` table.
    """

    __tablename__ = "forge_events_v1"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    event_digest = Column(String(64), nullable=False)
    schema_version = Column(String(32), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    service_name = Column(Text, nullable=False)
    service_instance_id = Column(Text, nullable=True)
    environment = Column(Text, nullable=False)
    tenant_ref = Column(Text, nullable=True)
    event_type = Column(Text, nullable=False)
    severity = Column(String(16), nullable=False)
    outcome = Column(String(32), nullable=False)
    evidence_class = Column(String(16), nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    trace_id = Column(String(32), nullable=True)
    span_id = Column(String(16), nullable=True)
    parent_span_id = Column(String(16), nullable=True)
    attributes = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    privacy_class = Column(String(16), nullable=False)
    retention_class = Column(String(16), nullable=False)
    sampled = Column(Boolean, nullable=False)
    sample_rate = Column(Float, nullable=True)
    sampling_reason = Column(String(32), nullable=False)


class ForgeCheckResultV1Record(Base):
    """Durable, scope-bound ForgeCheckResult.v1 evidence."""

    __tablename__ = "forge_check_results_v1"

    result_id = Column(UUID(as_uuid=True), primary_key=True)
    payload_digest = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    check_id = Column(Text, nullable=False, index=True)
    check_revision = Column(Integer, nullable=False)
    definition_sha256 = Column(String(64), nullable=False)
    environment = Column(Text, nullable=False, index=True)
    tenant_ref = Column(Text, nullable=True, index=True)
    evaluation_mode = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False)
    reason_code = Column(String(96), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    assertion_passed = Column(Boolean, nullable=True)
    slo_included = Column(Boolean, nullable=False)
    uptime_included = Column(Boolean, nullable=False)
    baseline_included = Column(Boolean, nullable=False)
    cost_units_observed = Column(Integer, nullable=False)
    privacy_class = Column(String(16), nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    trace_id = Column(String(32), nullable=True)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ForgeCheckRunReceiptV1Record(Base):
    """Durable ForgeCheckRunReceipt.v1 evidence linked to one result."""

    __tablename__ = "forge_check_run_receipts_v1"
    __table_args__ = (
        UniqueConstraint("result_id", name="uq_forge_check_receipt_result"),
    )

    receipt_id = Column(UUID(as_uuid=True), primary_key=True)
    payload_digest = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("forge_check_results_v1.result_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    check_id = Column(Text, nullable=False, index=True)
    definition_sha256 = Column(String(64), nullable=False)
    environment = Column(Text, nullable=False, index=True)
    tenant_ref = Column(Text, nullable=True, index=True)
    source_repository = Column(Text, nullable=False)
    source_commit = Column(String(40), nullable=False)
    source_path = Column(Text, nullable=False)
    runner_service_name = Column(Text, nullable=False)
    runner_version = Column(String(64), nullable=False)
    trigger = Column(String(16), nullable=False)
    evaluation_mode = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    slo_included = Column(Boolean, nullable=False)
    uptime_included = Column(Boolean, nullable=False)
    baseline_included = Column(Boolean, nullable=False)
    slo_reason = Column(String(32), nullable=False)
    max_cost_units = Column(Integer, nullable=False)
    observed_cost_units = Column(Integer, nullable=False)
    cost_unit = Column(String(16), nullable=False)
    kill_switch_ref = Column(Text, nullable=False)
    kill_switch_enabled = Column(Boolean, nullable=False)
    evidence_refs = Column(JSON, nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TelemetryDerivationReceiptV1Record(Base):
    """Immutable CP5 derivation provenance; never source evidence."""

    __tablename__ = "telemetry_derivation_receipts_v1"
    __table_args__ = (
        UniqueConstraint("derivation_id", name="uq_telemetry_derivation_id"),
        UniqueConstraint(
            "output_kind",
            "output_ref",
            name="uq_telemetry_derivation_output",
        ),
    )

    receipt_id = Column(UUID(as_uuid=True), primary_key=True)
    derivation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payload_digest = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    derivation_type = Column(String(32), nullable=False, index=True)
    producer_service_name = Column(Text, nullable=False)
    producer_version = Column(String(64), nullable=False)
    policy_id = Column(Text, nullable=False, index=True)
    policy_version = Column(String(64), nullable=False)
    policy_sha256 = Column(String(64), nullable=False)
    policy_mode = Column(String(16), nullable=False)
    clock_basis = Column(String(16), nullable=False)
    window_start_at = Column(DateTime(timezone=True), nullable=False)
    window_end_at = Column(DateTime(timezone=True), nullable=False, index=True)
    output_kind = Column(String(32), nullable=False)
    output_ref = Column(UUID(as_uuid=True), nullable=False)
    output_sha256 = Column(String(64), nullable=False)
    decision_action = Column(String(32), nullable=False)
    decision_reason_code = Column(String(96), nullable=False)
    decision_applied = Column(Boolean, nullable=False)
    source_overwritten = Column(Boolean, nullable=False)
    uncertainty_state = Column(String(16), nullable=False)
    source_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TelemetryRetentionDecisionV1Record(Base):
    """One shadow retention decision linked to exact source evidence."""

    __tablename__ = "telemetry_retention_decisions_v1"
    __table_args__ = (
        UniqueConstraint(
            "source_kind",
            "source_ref",
            "policy_sha256",
            "window_end_at",
            name="uq_telemetry_retention_source_policy_window",
        ),
    )

    decision_id = Column(UUID(as_uuid=True), primary_key=True)
    receipt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "telemetry_derivation_receipts_v1.receipt_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
    )
    source_kind = Column(String(32), nullable=False, index=True)
    source_ref = Column(Text, nullable=False, index=True)
    source_sha256 = Column(String(64), nullable=False)
    source_received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    service_or_check = Column(Text, nullable=False)
    environment = Column(Text, nullable=False, index=True)
    tenant_ref = Column(Text, nullable=True, index=True)
    privacy_class = Column(String(16), nullable=False)
    retention_class = Column(String(16), nullable=False)
    legal_class = Column(String(16), nullable=False)
    policy_id = Column(Text, nullable=False)
    policy_version = Column(String(64), nullable=False)
    policy_sha256 = Column(String(64), nullable=False)
    policy_mode = Column(String(16), nullable=False)
    clock_basis = Column(String(16), nullable=False)
    window_start_at = Column(DateTime(timezone=True), nullable=False)
    window_end_at = Column(DateTime(timezone=True), nullable=False)
    action = Column(String(32), nullable=False)
    reason_code = Column(String(96), nullable=False)
    projected_delete_at = Column(DateTime(timezone=True), nullable=True)
    applied = Column(Boolean, nullable=False)
    source_overwritten = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class TelemetryRoutineAggregateV1Record(Base):
    """Routine-success aggregate derived without replacing its sources."""

    __tablename__ = "telemetry_routine_aggregates_v1"
    __table_args__ = (
        UniqueConstraint(
            "group_key",
            "policy_sha256",
            "window_end_at",
            name="uq_telemetry_aggregate_group_policy_window",
        ),
    )

    aggregate_id = Column(UUID(as_uuid=True), primary_key=True)
    receipt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "telemetry_derivation_receipts_v1.receipt_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
    )
    payload_digest = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    group_key = Column(String(64), nullable=False, index=True)
    evidence_kind = Column(String(32), nullable=False)
    service_or_check = Column(Text, nullable=False)
    environment = Column(Text, nullable=False, index=True)
    tenant_ref = Column(Text, nullable=True, index=True)
    privacy_class = Column(String(16), nullable=False)
    retention_class = Column(String(16), nullable=False)
    decision_reason_code = Column(String(96), nullable=False)
    source_count = Column(Integer, nullable=False)
    window_start_at = Column(DateTime(timezone=True), nullable=False)
    window_end_at = Column(DateTime(timezone=True), nullable=False, index=True)
    policy_id = Column(Text, nullable=False)
    policy_version = Column(String(64), nullable=False)
    policy_sha256 = Column(String(64), nullable=False)
    policy_mode = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
