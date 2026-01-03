"""
Tarcie ingest service.

Handles batch ingestion of events from Tarcie.
Append-only storage with duplicate detection.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.tarcie_models import TarcieEvent
from app.models.tarcie_schemas import (
    TarcieEventIn,
    TarcieIngestRequest,
    TarcieIngestResponse,
)

logger = logging.getLogger(__name__)


class TarcieService:
    """Service for Tarcie event ingestion."""

    def __init__(self, db: Session):
        self.db = db

    def ingest_batch(self, request: TarcieIngestRequest) -> TarcieIngestResponse:
        """
        Ingest a batch of events from Tarcie.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
        Returns count of events ingested vs skipped (duplicates).
        """
        if not request.events:
            return TarcieIngestResponse(
                status="success",
                events_ingested=0,
                events_skipped=0,
                timestamp=datetime.utcnow(),
            )

        ingested = 0
        skipped = 0
        errors: list[str] = []

        # Get existing IDs to detect duplicates
        event_ids = [e.id for e in request.events]
        existing_ids = set(
            self.db.execute(
                select(TarcieEvent.id).where(TarcieEvent.id.in_(event_ids))
            ).scalars().all()
        )

        # Prepare events for bulk insert
        new_events = []
        for event in request.events:
            if event.id in existing_ids:
                skipped += 1
                continue

            new_events.append(self._event_to_dict(event))

        # Bulk insert with ON CONFLICT DO NOTHING for race condition safety
        if new_events:
            stmt = insert(TarcieEvent).values(new_events)
            stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
            result = self.db.execute(stmt)
            ingested = result.rowcount if result.rowcount else len(new_events)

        self.db.commit()

        logger.info(
            "tarcie_ingest_complete",
            extra={
                "events_ingested": ingested,
                "events_skipped": skipped,
                "batch_size": len(request.events),
            },
        )

        status = "success"
        if errors:
            status = "partial" if ingested > 0 else "error"

        return TarcieIngestResponse(
            status=status,
            events_ingested=ingested,
            events_skipped=skipped,
            errors=errors,
            timestamp=datetime.utcnow(),
        )

    def _event_to_dict(self, event: TarcieEventIn) -> dict:
        """Convert Pydantic model to dict for bulk insert."""
        return {
            "id": event.id,
            "device_id": event.device_id,
            "timestamp_utc": event.timestamp_utc,
            "timestamp_mono_ms": event.timestamp_mono_ms,
            "event_type": event.event_type,
            "content": event.content,
            "app_context": event.app_context,
            "source_version": event.source_version,
            "ingested_at": datetime.utcnow(),
        }

    def get_event_count(self, device_id: UUID | None = None) -> int:
        """Get total event count, optionally filtered by device."""
        from sqlalchemy import func

        query = select(func.count()).select_from(TarcieEvent)
        if device_id:
            query = query.where(TarcieEvent.device_id == device_id)
        return self.db.execute(query).scalar() or 0
