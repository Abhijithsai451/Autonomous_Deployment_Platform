from typing import Dict, Any
from uuid import UUID

from packages.events.base import BaseEvent


class WorkflowStartedEvent(BaseEvent):
    instance_id: UUID
    blueprint_id: UUID
    triggered_by: str = "SYSTEM"

    @property
    def subject(self) -> str:
        return "workflow.events.instance.started"

class TaskReadyEvent(BaseEvent):
    instance_id: UUID
    task_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}

    @property
    def subject(self) -> str:
        return "workflow.events.task.ready"


class TaskCompletedEvent(BaseEvent):
    instance_id: UUID
    task_id: UUID
    result: Dict[str, Any] = {}

    @property
    def subject(self) -> str:
        return "workflow.events.task.completed"