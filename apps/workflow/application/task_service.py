from datetime import datetime, timezone
from fastapi import HTTPException, status
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from apps.workflow.application.dependency_service import TaskDependencyEngine
from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus
from apps.workflow.domain.tasks import Task, TaskStatus
from apps.workflow.domain.workflow_events import WorkflowEvent


class TaskService:
    def __init__(self, db:Session):
        self.db = db
        self.dependency_engine = TaskDependencyEngine(db)

    def _log_event(self,instance_id: UUID,task_id: UUID,event_type: str,payload: dict) -> WorkflowEvent:
        event = WorkflowEvent(
            workflow_instance_id=instance_id,
            task_id=task_id,
            event_type=event_type,
            payload=payload,
        )
        self.db.add(event)

        outbox_entry = OutboxEvent(
            event_type=event_type,
            aggregate_type="Task",
            aggregate_id=task_id,
            payload={
                "task_id": str(task_id),
                "instance_id": str(instance_id),
                **payload
            },
            status=OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)

        return event

    def get_task_by_id(self, task_id: UUID) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found with id {task_id}"
            )
        return task

    def get_tasks_by_instance(self, instance_id: UUID) -> List[Task]:
        return self.db.query(Task).filter(Task.workflow_instance_id == instance_id).all()

    def mark_task_ready(self, task_id: UUID) -> Task:
        task =  self.get_task_by_id(task_id)
        task.mark_ready()

        self._log_event(task.workflow_instance_id, task.id, "TaskReady", {})
        self.db.commit()
        self.db.refresh(task)
        return task

    def start_task(self, task_id: UUID, assigned_agent_id: Optional[UUID] = None) -> Task:
        task = self.get_task_by_id(task_id)

        task.start()
        if assigned_agent_id:
            task.assigned_agent_id = assigned_agent_id

        self._log_event(
            task.workflow_instance_id,
            task.id,
            "TaskStarted",
            {"assigned_agent_id": str(assigned_agent_id) if assigned_agent_id else None}
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def complete_task(self, task_id: UUID, output_data: dict = None) -> Task:
        task = self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found.")

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        if output_data:
            task.output_data = output_data

        self._log_event(
            instance_id=task.workflow_instance_id,
            task_id=task.id,
            event_type="workflow.events.TaskCompleted",
            payload={"status": task.status.value}
        )

        self.dependency_engine.evaluate_downstream_tasks(task)

        self.db.commit()
        self.db.refresh(task)
        return task

    def fail_task(self, task_id: UUID, error_details: dict = None) -> Task:
        task = self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found.")

        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now(timezone.utc)
        task.error_details = error_details

        self._log_event(
            instance_id=task.workflow_instance_id,
            task_id=task.id,
            event_type="workflow.events.TaskFailed",
            payload={"status": task.status.value, "error": error_details}
        )

        self.dependency_engine.cascade_failure(task)

        self.db.commit()
        self.db.refresh(task)
        return task

    def retry_task(self, task_id: UUID) -> Task:
        task = self.get_task_by_id(task_id)
        task.retry()

        self._log_event(
            task.workflow_instance_id,
            task.id,
            "TaskRetried",
            {"retry_count": task.retry_count}
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def cancel_task(self, task_id: UUID, reason: str = "Cancelled by user") -> Task:
        task = self.get_task_by_id(task_id)

        task.cancel(reason=reason)

        self._log_event(task.workflow_instance_id, task.id, "TaskCancelled", {"reason": reason})
        self.db.commit()
        self.db.refresh(task)
        return task

    def request_approval(
            self,
            task_id: UUID,
            required_approvers: list = [],
            details: dict = {}
    ) -> Task:
        task = self.get_task_by_id(task_id)
        if task.status == TaskStatus.READY:
            task.start()

        payload = {"approvers": required_approvers, "details": details}
        self._log_event(task.workflow_instance_id, task.id, "ApprovalRequested", payload)

        self.db.commit()
        self.db.refresh(task)
        return task

    def receive_approval(
            self,
            task_id: UUID,
            approved_by: str,
            approval_metadata: dict = {}
    ) -> Task:
        task = self.get_task_by_id(task_id)

        if task.status != TaskStatus.RUNNING:
            raise InvalidStateTransitionError("Task", str(task.id), task.status.value, "receive_approval")

        payload = {"approved_by": approved_by, "metadata": approval_metadata}
        self._log_event(task.workflow_instance_id, task.id, "ApprovalReceived", payload)

        self.db.commit()
        self.db.refresh(task)
        return task