"""create CP6 evidence-grounded incident candidate storage

Revision ID: 20260725_03
Revises: 20260725_02
Create Date: 2026-07-25

Rollback revokes the isolated runtime role and its RLS policies while retaining
all candidate records. No source evidence is updated or deleted.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260725_03"
down_revision: str | None = "20260725_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_incident_candidates_v1 (
            candidate_id UUID PRIMARY KEY,
            payload_digest CHAR(64) NOT NULL
                CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
            payload JSONB NOT NULL
                CHECK (
                    jsonb_typeof(payload) = 'object'
                    AND payload ->> 'schema_version' = 'IncidentCandidate.v1'
                ),
            fingerprint_version TEXT NOT NULL
                CHECK (
                    fingerprint_version = 'incident-candidate-fingerprint.v1'
                ),
            fingerprint_sha256 CHAR(64) NOT NULL UNIQUE
                CHECK (fingerprint_sha256 ~ '^[0-9a-f]{64}$'),
            environment TEXT NOT NULL
                CHECK (environment ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            tenant_ref TEXT
                CHECK (
                    tenant_ref IS NULL
                    OR tenant_ref ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'
                ),
            correlation_id UUID,
            trace_ids JSONB NOT NULL
                CHECK (
                    jsonb_typeof(trace_ids) = 'array'
                    AND jsonb_array_length(trace_ids) <= 32
                ),
            window_clock_basis TEXT NOT NULL
                CHECK (window_clock_basis = 'evidence_observed_at'),
            window_start_at TIMESTAMPTZ NOT NULL,
            window_end_at TIMESTAMPTZ NOT NULL,
            suspected_cause_code TEXT NOT NULL
                CHECK (suspected_cause_code ~ '^[a-z0-9_]{1,96}$'),
            confidence_basis_points INTEGER NOT NULL
                CHECK (confidence_basis_points BETWEEN 0 AND 10000),
            confidence_method TEXT NOT NULL
                CHECK (
                    confidence_method IN (
                        'deterministic_rules',
                        'model_assisted'
                    )
                ),
            uncertainty_state TEXT NOT NULL
                CHECK (
                    uncertainty_state IN (
                        'complete',
                        'partial',
                        'unknown'
                    )
                ),
            privacy_class TEXT NOT NULL
                CHECK (
                    privacy_class IN (
                        'public',
                        'internal',
                        'restricted',
                        'confidential'
                    )
                ),
            analysis_kind TEXT NOT NULL
                CHECK (
                    analysis_kind IN (
                        'deterministic_rules',
                        'neuroforge_model'
                    )
                ),
            producer_service TEXT NOT NULL
                CHECK (
                    producer_service ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'
                ),
            producer_version TEXT NOT NULL
                CHECK (length(producer_version) BETWEEN 1 AND 64),
            provider TEXT,
            model TEXT,
            prompt_sha256 CHAR(64)
                CHECK (
                    prompt_sha256 IS NULL
                    OR prompt_sha256 ~ '^[0-9a-f]{64}$'
                ),
            model_response_sha256 CHAR(64)
                CHECK (
                    model_response_sha256 IS NULL
                    OR model_response_sha256 ~ '^[0-9a-f]{64}$'
                ),
            run_receipt_ref TEXT,
            candidate_only BOOLEAN NOT NULL CHECK (candidate_only),
            can_repair BOOLEAN NOT NULL CHECK (NOT can_repair),
            can_rollback BOOLEAN NOT NULL CHECK (NOT can_rollback),
            can_notify BOOLEAN NOT NULL CHECK (NOT can_notify),
            can_promote BOOLEAN NOT NULL CHECK (NOT can_promote),
            requires_human_decision BOOLEAN NOT NULL
                CHECK (requires_human_decision),
            source_overwritten BOOLEAN NOT NULL CHECK (NOT source_overwritten),
            created_at TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            CHECK (window_end_at >= window_start_at),
            CHECK (created_at >= window_end_at),
            CHECK (payload ->> 'environment' = environment),
            CHECK ((payload ->> 'tenant_ref') IS NOT DISTINCT FROM tenant_ref),
            CHECK (
                payload #>> '{window,clock_basis}' = window_clock_basis
                AND payload #>> '{suspected_cause,cause_code}'
                    = suspected_cause_code
                AND payload #>> '{confidence,method}' = confidence_method
                AND payload #>> '{uncertainty,state}' = uncertainty_state
                AND payload ->> 'privacy_class' = privacy_class
            ),
            CHECK (
                payload #>> '{deduplication,fingerprint_version}'
                    = fingerprint_version
                AND payload #>> '{deduplication,fingerprint_sha256}'
                    = fingerprint_sha256
            ),
            CHECK (
                payload #>> '{analysis_provenance,analysis_kind}'
                    = analysis_kind
                AND payload #>> '{analysis_provenance,producer_service}'
                    = producer_service
                AND payload #>> '{analysis_provenance,producer_version}'
                    = producer_version
            ),
            CHECK (
                (analysis_kind = 'deterministic_rules'
                    AND confidence_method = 'deterministic_rules'
                    AND provider IS NULL
                    AND model IS NULL
                    AND prompt_sha256 IS NULL
                    AND model_response_sha256 IS NULL
                    AND run_receipt_ref IS NULL)
                OR
                (analysis_kind = 'neuroforge_model'
                    AND producer_service = 'neuroforge'
                    AND confidence_method = 'model_assisted'
                    AND provider IS NOT NULL
                    AND model IS NOT NULL
                    AND prompt_sha256 IS NOT NULL
                    AND model_response_sha256 IS NOT NULL
                    AND run_receipt_ref IS NOT NULL)
            ),
            CHECK (
                payload #>> '{authority,classification}'
                    = 'derived_candidate'
                AND (payload #>> '{authority,candidate_only}')::BOOLEAN
                    IS TRUE
                AND (payload #>> '{authority,can_repair}')::BOOLEAN
                    IS FALSE
                AND (payload #>> '{authority,can_rollback}')::BOOLEAN
                    IS FALSE
                AND (payload #>> '{authority,can_notify}')::BOOLEAN
                    IS FALSE
                AND (payload #>> '{authority,can_promote}')::BOOLEAN
                    IS FALSE
                AND (
                    payload #>> '{authority,requires_human_decision}'
                )::BOOLEAN IS TRUE
                AND (payload #>> '{authority,source_overwritten}')::BOOLEAN
                    IS FALSE
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_incident_candidates_scope_created
        ON telemetry_incident_candidates_v1 (
            md5(environment),
            md5(COALESCE(tenant_ref, '')),
            created_at DESC
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_incident_candidates_correlation
        ON telemetry_incident_candidates_v1 (correlation_id)
        WHERE correlation_id IS NOT NULL
        """
    )
    op.execute(
        "ALTER TABLE telemetry_incident_candidates_v1 ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "REVOKE ALL ON TABLE telemetry_incident_candidates_v1 FROM PUBLIC"
    )
    op.execute(
        """
        GRANT SELECT, INSERT
        ON TABLE telemetry_incident_candidates_v1
        TO dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS telemetry_incident_candidates_runtime_insert
        ON telemetry_incident_candidates_v1
        """
    )
    op.execute(
        """
        CREATE POLICY telemetry_incident_candidates_runtime_insert
        ON telemetry_incident_candidates_v1
        FOR INSERT TO dataforge_telemetry_ingest
        WITH CHECK (
            candidate_only
            AND NOT can_repair
            AND NOT can_rollback
            AND NOT can_notify
            AND NOT can_promote
            AND requires_human_decision
            AND NOT source_overwritten
        )
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS telemetry_incident_candidates_runtime_select
        ON telemetry_incident_candidates_v1
        """
    )
    op.execute(
        """
        CREATE POLICY telemetry_incident_candidates_runtime_select
        ON telemetry_incident_candidates_v1
        FOR SELECT TO dataforge_telemetry_ingest
        USING (
            candidate_only
            AND NOT can_repair
            AND NOT can_rollback
            AND NOT can_notify
            AND NOT can_promote
            AND requires_human_decision
            AND NOT source_overwritten
        )
        """
    )


def downgrade() -> None:
    """Disable runtime access while retaining every CP6 candidate record."""

    op.execute(
        """
        DROP POLICY IF EXISTS telemetry_incident_candidates_runtime_select
        ON telemetry_incident_candidates_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS telemetry_incident_candidates_runtime_insert
        ON telemetry_incident_candidates_v1
        """
    )
    op.execute(
        """
        REVOKE SELECT, INSERT
        ON TABLE telemetry_incident_candidates_v1
        FROM dataforge_telemetry_ingest
        """
    )
