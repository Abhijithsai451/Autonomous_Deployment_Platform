from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.domain.outbox import OutboxEvent, OutboxStatus


class OutboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self,event_type: str,aggregate_type: str,aggregate_id: Optional[UUID],payload: Dict[str, Any]
    ) -> OutboxEvent:
        outbox_event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status="PENDING",
            retry_count=0,
            max_retries=5,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(outbox_event)
        self.db.flush()
        return outbox_event

    def get_by_id(self, outbox_id: UUID) -> Optional[OutboxEvent]:
        return self.db.query(OutboxEvent).filter(OutboxEvent.id == outbox_id).first()

    def get_latest_by_aggregate(self, aggregate_id: UUID) -> Optional[OutboxEvent]:
        return (
            self.db.query(OutboxEvent)
            .filter(OutboxEvent.aggregate_id == aggregate_id)
            .order_by(OutboxEvent.created_at.desc())
            .first()
        )
    def get_pending_events(self, batch_size: int = 20)-> List[OutboxEvent]:
        events = (self.db.query(OutboxEvent).filter(OutboxEvent.status == OutboxStatus.PENDING)
                  .order_by(OutboxEvent.created_at.asc()).limit(batch_size).all())
        return events

    def mark_processing(self, event_id: UUID) -> Optional[OutboxEvent]:
        event = self.db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if event:
            event.status = OutboxStatus.PROCESSING
            self.db.flush()
        return event

    def mark_published(self, event_id: UUID) -> Optional[OutboxEvent]:
        event = self.db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if event:
            event.status = OutboxStatus.PUBLISHED
            event.processed_at = datetime.now(timezone.utc)
            self.db.flush()
        return event

    def record_failure(self, event_id: UUID, error_message: str) -> Optional[OutboxEvent]:
        event = self.db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if event:
            event.retry_count += 1
            event.last_error = error_message
            event.error_message = error_message

            if event.retry_count >= event.max_retries:
                event.status = OutboxStatus.FAILED
            else:
                event.status = OutboxStatus.PENDING

            self.db.flush()
        return event


