from typing import Dict, Any, Optional, Type
from uuid import UUID

from packages.events.base import BaseEvent
from packages.events.event_registry import EventRegistry


def register_event(cls:Type[BaseEvent])-> Type[BaseEvent]:
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

class WorkflowLifeCycleEvent(BaseEvent):
    instance_id: Optional[UUID]
    blueprint_id:Optional[UUID]
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
        return "workflow.events.instance.resumed"

class WorkflowCompletedEvent(WorkflowLifeCycleEvent):
    output_data: Dict[str, Any] = {}
    @property
    def subject(self) -> str:
        return "workflow.events.instance.completed"

class WorkflowFailedEvent(WorkflowLifeCycleEvent):
    error_message: str
    failed_step_id: Optional[UUID] = None
    @property
    def subject(self) -> str:
        return "workflow.events.instance.failed"

class WorkflowCancelledEvent(WorkflowLifeCycleEvent):
    cancelled_by: str
    reason: Optional[str] = None
    @property
    def subject(self) -> str:
        return "workflow.events.instance.cancelled"

class WorkflowRetryEvent(WorkflowLifeCycleEvent):
    reason: Optional[str] = None
    @property
    def subject(self) -> str:
        return "workflow.events.instance.retry"

class WorkflowTimedOutEvent(WorkflowLifeCycleEvent):
    timeout_seconds: int
    @property
    def subject(self) -> str:
        return "workflow.events.instance.timed_out"

class WorkflowSignalInstanceEvent(WorkflowLifeCycleEvent):
    @property
    def subject(self) -> str:
        return "workflow.events.instance.signal_instance"

class WorkflowInstanceCreated(WorkflowLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "workflow.events.instance.created"

class WorkflowInstanceNotFound(WorkflowLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "workflow.events.instance.not_found"

class BlueprintLifeCycleEvent(BaseEvent):
    pass


class BlueprintCreatedEvent(BlueprintLifeCycleEvent):
    id: UUID
    @property
    def subject(self)->str:
        return "workflow.events.blueprint.created"

class BlueprintAlreadyExists(BlueprintLifeCycleEvent):
    name : str
    @property
    def subject(self)-> str:
        return "workflow.events.blueprint.already_exists"

class BlueprintUpdateEvent(BlueprintCreatedEvent):
    id: UUID
    @property
    def subject(self)-> str:
        return "workflow.events.blueprint.updated"


class ApprovalLifecycleEvent(BaseEvent):
    instance_id: UUID
    task_id: UUID
    approval_id: UUID


class ApprovalRequestedEvent(ApprovalLifecycleEvent):
    approver_role: str
    context_data: Dict[str, Any] = {}

    @property
    def subject(self) -> str:
        return "workflow.events.approval.requested"


class ApprovalReceivedEvent(ApprovalLifecycleEvent):
    responded_by: str
    decision: str

    @property
    def subject(self) -> str:
        return "workflow.events.approval.received"


class ApprovalGrantedEvent(ApprovalLifecycleEvent):
    approved_by: str
    comments: Optional[str] = None

    @property
    def subject(self) -> str:
        return "workflow.events.approval.granted"


class ApprovalRejectedEvent(ApprovalLifecycleEvent):
    rejected_by: str
    reason: str

    @property
    def subject(self) -> str:
        return "workflow.events.approval.rejected"


