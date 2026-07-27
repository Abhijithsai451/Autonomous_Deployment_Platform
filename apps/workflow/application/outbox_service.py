from typing import Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus


class OutboxService:

    @staticmethod
    def stage_event(
        db: Session,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: Dict[str, Any]
    ) -> OutboxEvent:
        """
        Stages an outbox record in the active database session.
        MUST be committed along with the domain model changes.
        """
        outbox_entry = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status=OutboxStatus.PENDING
        )
        db.add(outbox_entry)
        return outbox_entry