from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from apps.workflow.domain.events.instance_events import WorkflowInstanceCreated, WorkflowInstanceNotFound, \
    WorkflowStartedEvent, WorkflowCompletedEvent, WorkflowFailedEvent, WorkflowPausedEvent, WorkflowResumedEvent, \
    WorkflowCancelledEvent, WorkflowRetryEvent, WorkflowTimedOutEvent, WorkflowSignalInstanceEvent
from apps.workflow.domain.events.tasks_events import TaskReadyEvent
from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus
from apps.workflow.domain.tasks import Task, TaskStatus
from apps.workflow.domain.workflow_event import WorkflowEvent
from apps.workflow.domain.workflow_instance import WorkflowInstance, WorkflowStatus


class InstanceService:
    def __init__(self, db: Session):
        self.db = db

    def _log_event(self, aggregate_id: UUID, aggregate_type: str, event_type: str, payload: dict):
        outbox_entry = OutboxEvent(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)

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
            aggregate_id=instance.id,
            aggregate_type = "INSTANCE",
            event_type= WorkflowInstanceCreated(instance_id = instance.id, blueprint_id= instance.blueprint_id).subject,
            payload={
                "id": str(instance.id),
                "blueprint_id": str(blueprint_id),
                "triggered_by": triggered_by,
                "status": instance.status,
            }
        )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def start_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            self._log_event(
                aggregate_id=instance_id,
                aggregate_type="INSTANCE",
                event_type=WorkflowInstanceNotFound(instance_id=instance_id).subject,
                payload={
                    "id": str(instance_id),
                    "error": f"Instance with the id {instance_id} not found",
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )

        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.now(timezone.utc)

        self._log_event(
            aggregate_id= instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowStartedEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id).subject,
            payload={
                "id": str(instance.id),
                "blueprint_id": str(instance.blueprint_id),
                "triggered_by": instance.triggered_by,
                "status": instance.status,
            })

        root_tasks = (
            self.db.query(Task)
            .filter(
                Task.workflow_instance_id == instance_id,
                Task.status == TaskStatus.PENDING,
                Task.dependencies.any()
            )
            .all()
        )

        for task in root_tasks:
            task.status = TaskStatus.READY
            self._log_event(
                aggregate_id=instance.id,
                aggregate_type="Task",
                event_type=TaskReadyEvent(task_id=task.id,
                                 instance_id=task.workflow_instance_id,
                                 action_type=task.action_type,
                                 input_data=task.input_data
                                 ).subject,
                payload={"task_id": str(task.id), "action_type": task.action_type}
            )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def complete_instance(self, instance_id: UUID, output_data: Optional[dict] = None) -> WorkflowInstance:
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            self._log_event(
                aggregate_id=instance_id,
                aggregate_type="INSTANCE",
                event_type=WorkflowInstanceNotFound(instance_id=instance_id).subject,
                payload={
                    "id": str(instance_id),
                    "error": f"Instance with the id {instance_id} not found",
                })

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )

        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = datetime.now(timezone.utc)
        if output_data:
            instance.output_data = output_data

        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowCompletedEvent(instance_id= instance.id, blueprint_id= instance.blueprint_id,
                                              output_data=instance.output_data).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
                "completed_at": str(instance.completed_at),
                "output_data": str(instance.output_data)
            }
        )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def fail_instance(self, instance_id: UUID, error_details: Optional[dict] = None) -> WorkflowInstance:
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            self._log_event(
                aggregate_id=instance_id,
                aggregate_type="INSTANCE",
                event_type=WorkflowInstanceNotFound(instance_id=instance_id).subject,
                payload={
                    "id": str(instance_id),
                    "error": f"Instance with the id {instance_id} not found",
                })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )

        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.now(timezone.utc)
        if error_details:
            instance.error_details = error_details

        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowFailedEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id,
                                              error_message=instance.error_details).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "error_message": str(instance.error_details)
            }
        )

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get_instance_by_id(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.db.get(WorkflowInstance, instance_id)
        if not instance:
            self._log_event(
                aggregate_id=instance_id,
                aggregate_type="INSTANCE",
                event_type=WorkflowInstanceNotFound(instance_id=instance_id).subject,
                payload={
                    "id": str(instance_id),
                    "error": f"Instance with the id {instance_id} not found",
                })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkflowInstance with ID {instance_id} not found."
            )
        return instance

    def list_instances(self, limit: int = 100, offset: int = 0) -> List[WorkflowInstance]:
        return self.db.query(WorkflowInstance).offset(offset).limit(limit).all()

    def get_instances(self, limit: int = 20, offset: int = 0,
                      status_filter: Optional[str] = None,
                      blueprint_id: Optional[UUID] = None
                      ) -> Dict[str, Any]:
        query = self.db.query(WorkflowInstance)

        if status_filter:
            if isinstance(status_filter, str):
                try:
                    enum_status = WorkflowStatus[status_filter.upper()]
                    query = query.filter(WorkflowInstance.status == enum_status)
                except KeyError:
                    query = query.filter(WorkflowInstance.status == status_filter)
            else:
                query = query.filter(WorkflowInstance.status == status_filter)

        if blueprint_id:
            query = query.filter(WorkflowInstance.blueprint_id == blueprint_id)

        total = query.count()

        instances = (
            query.order_by(WorkflowInstance.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            inst.to_dict() if hasattr(inst, "to_dict") else {
                "id": str(inst.id),
                "blueprint_id": str(inst.blueprint_id),
                "status": inst.status.value if hasattr(inst.status, "value") else str(inst.status),
                "input_data": inst.input_data,
                "output_data": getattr(inst, "output_data", None),
                "triggered_by": inst.triggered_by,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
                "completed_at": inst.completed_at.isoformat() if getattr(inst, "completed_at", None) else None,
            }
            for inst in instances
        ]

        return {"items": items,"total": total,"limit": limit,"offset": offset,"has_more": (offset + len(instances)) < total}

    def pause_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.PAUSED
        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowPausedEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
            }
        )
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def resume_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.RUNNING
        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowResumedEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
            }
        )
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def cancel_instance(self, instance_id: UUID, reason: str = "Cancelled") -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.now(timezone.utc)
        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowCancelledEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id,
                                              cancelled_by=instance.triggered_by).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
                "cancelled_by": instance.triggered_by
            }
        )
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def retry_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.RUNNING
        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowRetryEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id,
                                              triggered_by=instance.triggered_by).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
                "triggered_by": instance.triggered_by
            }
        )
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def timeout_instance(self, instance_id: UUID, reason: str = "Execution Timeout Reached") -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.now(timezone.utc)
        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowTimedOutEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id,
                                          timeout_seconds=10).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
            }
        )
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def signal_instance(self, instance_id: UUID, signal_name: str, payload: dict = None) -> WorkflowInstance:
        instance = self.get_instance_by_id(instance_id)
        self._log_event(
            aggregate_id=instance.id,
            aggregate_type="INSTANCE",
            event_type=WorkflowSignalInstanceEvent(instance_id=instance.id, blueprint_id=instance.blueprint_id).subject,
            payload={
                "id": str(instance_id),
                "blueprint_id": str(instance.blueprint_id),
                "status": instance.status.value,
            }
        )
        self.db.commit()
        self.db.refresh(instance)
        return instance
