from datetime import timezone, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.domain.processed_event import ProcessedEvent


class ProcessedEventsRepository:
    def __init__(self, db: Session ):
        self.db = db

    def is_processed(self, event_id: UUID, consumer_group: str)-> bool:
        return (
            self.db.query(ProcessedEvent)
            .filter(
                ProcessedEvent.event_id == event_id,
                ProcessedEvent.consumer_group== consumer_group
            )
            .first()
            is not None
            )

    def mark_processed(self, event_id: str, consumer_group: str)-> ProcessedEvent:
        processed_event = ProcessedEvent(
            event_id = event_id,
            consumer_group=consumer_group,
            processed_at = datetime.now(timezone.utc)
        )
        self.db.add(processed_event)
        self.db.flush()
        return processed_event
