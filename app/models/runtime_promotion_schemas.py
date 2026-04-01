from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_ALLOWED_SERVICES = {
    "df_local_foundation",
    "neuronforge_local",
    "cortex",
    "fa_local",
}

_ALLOWED_SEVERITIES = {
    "low",
    "moderate",
    "high",
    "critical",
}

_ALLOWED_FAILURE_PATTERN_TYPES = {
    "migration_failure",
    "compatibility_failure",
    "readiness_false_positive",
    "readiness_false_negative",
    "degraded_state_anomaly",
}


class LocalFailurePatternPayload(BaseModel):
    pattern_id: str = Field(..., min_length=1, max_length=255)
    failure_pattern_type: str = Field(..., min_length=1, max_length=100)
    frequency_window: str = Field(..., min_length=1, max_length=100)
    occurrence_count: int = Field(..., ge=1)
    severity: str = Field(..., min_length=1, max_length=20)
    affected_contract_or_capability: str | None = Field(default=None, max_length=255)
    supporting_examples: list[str] = Field(default_factory=list, max_length=25)

    @field_validator("pattern_id", "frequency_window")
    @classmethod
    def validate_non_blank_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be empty")
        return normalized

    @field_validator("failure_pattern_type")
    @classmethod
    def validate_failure_pattern_type(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in _ALLOWED_FAILURE_PATTERN_TYPES:
            raise ValueError(
                "failure_pattern_type must be one of: "
                + ", ".join(sorted(_ALLOWED_FAILURE_PATTERN_TYPES))
            )
        return normalized

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in _ALLOWED_SEVERITIES:
            raise ValueError(
                "severity must be one of: " + ", ".join(sorted(_ALLOWED_SEVERITIES))
            )
        return normalized

    @field_validator("affected_contract_or_capability")
    @classmethod
    def validate_optional_capability(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("affected_contract_or_capability cannot be blank")
        return normalized

    @field_validator("supporting_examples")
    @classmethod
    def validate_supporting_examples(cls, value: list[str]) -> list[str]:
        normalized_examples: list[str] = []
        for example in value:
            normalized = example.strip()
            if not normalized:
                raise ValueError("supporting_examples cannot contain blank values")
            normalized_examples.append(normalized)
        return normalized_examples


class LocalFailurePatternIngestRequest(BaseModel):
    envelope_type: Literal["local_failure_pattern"]
    envelope_version: Literal["v1"]
    fleet_member_id: str = Field(..., min_length=1, max_length=255)
    runtime_bundle_id: str | None = Field(default=None, max_length=255)
    runtime_bundle_version: str | None = Field(default=None, max_length=100)
    service: str = Field(..., min_length=1, max_length=100)
    dedupe_key: str | None = Field(default=None, max_length=255)
    observed_at: datetime
    payload: LocalFailurePatternPayload

    @field_validator(
        "fleet_member_id",
        "dedupe_key",
        "runtime_bundle_id",
        "runtime_bundle_version",
    )
    @classmethod
    def validate_optional_trimmed_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank")
        return normalized

    @field_validator("service")
    @classmethod
    def validate_service(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in _ALLOWED_SERVICES:
            raise ValueError(
                "service must be one of: " + ", ".join(sorted(_ALLOWED_SERVICES))
            )
        return normalized


class RuntimePromotionIngestAck(BaseModel):
    receipt_id: str
    envelope_type: Literal["local_failure_pattern"]
    envelope_version: Literal["v1"]
    status: Literal["accepted"]
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)