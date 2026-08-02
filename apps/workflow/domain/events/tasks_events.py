from typing import Dict, Any, Type
from uuid import UUID

from packages.events.base import BaseEvent
from packages.events.event_registry import EventRegistry


def register_event(cls: Type[BaseEvent])-> Type[BaseEvent]:
    EventRegistry.register(cls)
    return cls


class TaskLifeCycleEvent(BaseEvent):
    instance_id: UUID
    task_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}


class TaskCreatedEvent(TaskLifeCycleEvent):
    input_data: Dict[str, Any] = {}
    @property
    def subject(self)->str:
        return "workflow.events.task.created"


class TaskStartedEvent(TaskLifeCycleEvent):
    @property
    def subject(self)->str:
        return "workflow.events.task.started"


class TaskCompletedEvent(TaskLifeCycleEvent):
    result: Dict[str, Any] = {}
    @property
    def subject(self)->str:
        return "workflow.events.task.completed"


class TaskFailedEvent(TaskLifeCycleEvent):
    error_message: str
    @property
    def subject(self)->str:
        return "workflow.events.task.failed"


