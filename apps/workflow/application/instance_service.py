from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus
from apps.workflow.domain.tasks import Task, TaskStatus
from apps.workflow.domain.workflow_events import WorkflowEvent
from apps.workflow.domain.workflow_instance import WorkflowInstance, WorkflowStatus


class InstanceService:
    def __init__(self, db: Session):
        self.db = db

    def _log_event(self, instance_id: UUID, event_type: str, payload: dict) -> WorkflowEvent:
        event = WorkflowEvent(
            workflow_instance_id=instance_id,
            task_id=None,
            event_type=f"workflow.events.{event_type}",
            payload=payload,
        )
        self.db.add(event)

        outbox_entry = OutboxEvent(event_type=f"workflow.events.{event_type}",aggregate_type="WorkflowInstance",
            aggregate_id=instance_id,payload={"instance_id": str(instance_id),**payload},
            status=OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)
        return event

    def create_instance(self,blueprint_id: UUID,input_data: Optional[dict] = None,triggered_by: Optional[str] = "SYSTEM",
            started_by: Optional[str] = None) -> WorkflowInstance:
        actor = started_by or triggered_by or "SYSTEM"
        instance = WorkflowInstance(
            blueprint_id=blueprint_id,
            status=WorkflowStatus.PENDING,
            input_data=input_data or {},
            triggered_by=triggered_by
        )
        self.db.add(instance)
        self.db.flush()

        self._log_event(
            instance_id=instance.id,
            event_type="WorkflowCreated",
            payload={"blueprint_id": str(blueprint_id), "triggered_by": triggered_by}
        )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def start_instance(self, instance_id: UUID) -> WorkflowInstance:
        """Starts a workflow instance and unlocks initial root tasks (tasks with no dependencies)."""
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )

        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.now(timezone.utc)

        self._log_event(
            instance_id=instance.id,
            event_type="WorkflowStarted",
            payload={"blueprint_id": str(instance.blueprint_id)}
        )

        # Unlock initial root tasks (tasks without dependencies) for this instance
        root_tasks = (
            self.db.query(Task)
            .filter(
                Task.workflow_instance_id == instance_id,
                Task.status == TaskStatus.PENDING,
                ~Task.dependencies.any()  # Root task check
            )
            .all()
        )

        for task in root_tasks:
            task.status = TaskStatus.READY
            self._log_event(
                instance_id=instance.id,
                event_type="TaskReady",
                payload={"task_id": str(task.id), "action_type": task.action_type}
            )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def complete_instance(self, instance_id: UUID, output_data: Optional[dict] = None) -> WorkflowInstance:
        """Marks a workflow instance as COMPLETED."""
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )

        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = datetime.now(timezone.utc)
        if output_data:
            instance.output_data = output_data

        self._log_event(
            instance_id=instance.id,
            event_type="WorkflowCompleted",
            payload={"status": instance.status.value}
        )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def fail_instance(self, instance_id: UUID, error_details: Optional[dict] = None) -> WorkflowInstance:
        """Marks a workflow instance as FAILED."""
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )

        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.now(timezone.utc)
        if error_details:
            instance.error_details = error_details

        self._log_event(
            instance_id=instance.id,
            event_type="WorkflowFailed",
            payload={"status": instance.status.value, "error": error_details}
        )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get_instance_by_id(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )
        return instance

    def list_instances(self, limit: int = 100, offset: int = 0) -> List[WorkflowInstance]:
        return self.db.query(WorkflowInstance).offset(offset).limit(limit).all()

    def get_instances(self, limit: int = 100, offset: int = 0) -> List[WorkflowInstance]:
        return self.list_instances(limit=limit, offset=offset)

    def pause_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.PAUSED
        self._log_event(instance.id, "WorkflowPaused", {})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def resume_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.RUNNING
        self._log_event(instance.id, "WorkflowResumed", {})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def cancel_instance(self, instance_id: UUID, reason: str = "Cancelled") -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.now(timezone.utc)
        self._log_event(instance.id, "WorkflowCancelled", {"reason": reason})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def retry_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.RUNNING
        self._log_event(instance.id, "WorkflowRetried", {})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def timeout_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.now(timezone.utc)
        self._log_event(instance.id, "WorkflowTimedOut", {"reason": "Timeout reached"})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def signal_instance(self, instance_id: UUID, signal_name: str, payload: dict = None) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        self._log_event(instance.id, f"SignalReceived.{signal_name}", payload or {})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    """ def timeout_instance(self, instance_id: UUID, reason: str = "Timeout reached") -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.now(timezone.utc)
        self._log_event(instance.id, "WorkflowTimedOut", {"reason": reason})
        self.db.commit()
        self.db.refresh(instance)
        return instance"""