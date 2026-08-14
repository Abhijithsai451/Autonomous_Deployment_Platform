from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from apps.workflow.domain.workflow_event import WorkflowEvent

class TimelineService:
    def __init__(self, db:Session):
        self.db = db

    def get_instance_timeline(self, instance_id: UUID) -> List[WorkflowEvent]:
        return (
            self.db.query(WorkflowEvent)
            .filter(WorkflowEvent.workflow_instance_id == instance_id)
            .order_by(WorkflowEvent.created_at.asc())
            .all()
        )