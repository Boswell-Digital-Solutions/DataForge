from __future__ import annotations

from hashlib import sha256
import json

from app.models.runtime_promotion_candidate_models import RuntimePromotionCandidate
from app.models.runtime_promotion_models import RuntimePromotionReceipt


def build_candidate_id(receipt: RuntimePromotionReceipt) -> str:
    digest = sha256(
        json.dumps(
            {
                "receipt_id": receipt.receipt_id,
                "service": receipt.service,
                "source_envelope_type": receipt.envelope_type,
                "payload": receipt.payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"rpc_{digest[:24]}"


def build_candidate_from_receipt(
    receipt: RuntimePromotionReceipt,
) -> RuntimePromotionCandidate:
    payload = receipt.payload or {}

    issue_class = str(payload.get("failure_pattern_type", "unknown"))
    severity = str(payload.get("severity", "moderate"))
    service = receipt.service
    fleet_member_id = receipt.fleet_member_id

    title = f"{service} reported {issue_class.replace('_', ' ')}"
    summary = (
        f"Accepted runtime-promotion receipt from {fleet_member_id} for "
        f"{service} indicating {issue_class.replace('_', ' ')}."
    )

    evidence = {
        "receipt_id": receipt.receipt_id,
        "dedupe_key": receipt.dedupe_key,
        "observed_at": receipt.observed_at.isoformat(),
        "supporting_examples": payload.get("supporting_examples", []),
        "affected_contract_or_capability": payload.get(
            "affected_contract_or_capability"
        ),
        "occurrence_count": payload.get("occurrence_count"),
        "frequency_window": payload.get("frequency_window"),
    }

    return RuntimePromotionCandidate(
        candidate_id=build_candidate_id(receipt),
        receipt_id=receipt.receipt_id,
        candidate_type="runtime_improvement_recommendation",
        source_envelope_type=receipt.envelope_type,
        service=service,
        fleet_member_id=fleet_member_id,
        issue_class=issue_class,
        severity=severity,
        title=title,
        summary=summary,
        evidence=evidence,
        source_payload=payload,
        status="review_ready",
        source="runtime_promotion",
    )