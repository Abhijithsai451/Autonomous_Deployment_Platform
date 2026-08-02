from typing import Dict, Any, Optional, Type
from uuid import UUID

from packages.events.base import BaseEvent
from packages.events.event_registry import EventRegistry


class WorkflowLifeCycleEvent(BaseEvent):
    instance_id: UUID
    blueprint_id: UUID
    triggered_by: str = "SYSTEM"

class WorkflowStartedEvent(WorkflowLifeCycleEvent):
    @property
    def subject(self)->str:
        return "workflow.events.instance.started"

class WorkflowPausedEvent(WorkflowLifeCycleEvent):
    reason: Optional[str] = None
    @property
    def subject(self)-> str:
        return "workflow.events.instance.paused"

class WorkflowResumedEvent(WorkflowLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "workflow.event.instance.resumed"

class WorkflowCompletedEvent(WorkflowLifeCycleEvent):
    output_data: Dict[str, Any] = {}
    @property
    def subject(self) -> str:
        return "workflow.event.instance.completed"

class WorkflowFailedEvent(WorkflowLifeCycleEvent):
    error_message: str
    failed_step_id: Optional[UUID] = None
    @property
    def subject(self) -> str:
        return "workflow.event.instance.failed"

class WorkflowCancelledEvent(WorkflowLifeCycleEvent):
    cancelled_by: str
    reason: Optional[str] = None
    @property
    def subject(self) -> str:
        return "workflow.event.instance.cancelled"

class WorkflowTimedOutEvent(WorkflowLifeCycleEvent):
    timeout_seconds: int
    @property
    def subject(self) -> str:
        return "workflow.event.instance.timedout"


