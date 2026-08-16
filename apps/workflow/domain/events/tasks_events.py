from typing import Dict, Any, Type
from uuid import UUID

from packages.events.base import BaseEvent
from packages.events.event_registry import EventRegistry


def register_event(cls: Type[BaseEvent])-> Type[BaseEvent]:
    EventRegistry.register(cls)
    return cls


class TaskLifeCycleEvent(BaseEvent):
    task_id: UUID

class TaskCreatedEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    @property
    def subject(self)->str:
        return "workflow.events.task.created"

class TaskReadyEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    @property
    def subject(self)-> str:
        return "workflow.events.task.ready"

class TaskStartedEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    @property
    def subject(self)->str:
        return "workflow.events.task.started"


class TaskCompletedEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    result: Dict[str, Any] = {}
    @property
    def subject(self)->str:
        return "workflow.events.task.completed"


class TaskFailedEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    error_message: str
    @property
    def subject(self)->str:
        return "workflow.events.task.failed"

class TaskRetryEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    @property
    def subject(self)-> str:
        return "workflow.events.task.retry"

class TaskCancelEvent(TaskLifeCycleEvent):
    instance_id: UUID
    action_type: str
    input_data: Dict[str, Any] = {}
    @property
    def subject(self)-> str:
        return "workflow.events.task.cancel"

class TaskNotFoundEvent(TaskLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "workflow.events.task.not_found"

