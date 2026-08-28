from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.domain.outbox import OutboxEvent


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

