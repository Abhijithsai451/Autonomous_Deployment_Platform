from typing import Dict, Any, Optional, Type
from uuid import UUID

from packages.events.base import BaseEvent
from packages.events.event_registry import EventRegistry


def register_event(cls:Type[BaseEvent])-> Type[BaseEvent]:
    EventRegistry.register(cls)
    return cls


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
    decision: str  # "GRANTED" or "REJECTED"

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