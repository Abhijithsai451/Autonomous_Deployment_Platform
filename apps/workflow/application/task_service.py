from datetime import datetime
from fastapi import HTTPException, status
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.domain.tasks import Task, TaskStatus
from apps.workflow.domain.workflow_events import WorkflowEvent
from infrastructure.nats.nats_client import EventBus


class TaskService:
    def __init__(self, db:Session):
        self.db = db

    def _log_event(
            self,
            instance_id: UUID,
            task_id: UUID,
            event_type: str,
            payload: dict
    ) -> WorkflowEvent:
        """Stages an internal audit log event within the current DB session."""
        event = WorkflowEvent(
            workflow_instance_id=instance_id,
            task_id=task_id,
            event_type=event_type,
            payload=payload,
        )
        self.db.add(event)
        return event

    async def get_task_by_id(self, task_id: UUID) -> Task:
        """Retrieves a task by ID or raises a 404 HTTPException."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found with id {task_id}"
            )
        return task

    async def get_tasks_by_instance(self, instance_id: UUID) -> List[Task]:
        """Retrieves all tasks associated with a workflow instance."""
        return self.db.query(Task).filter(Task.workflow_instance_id == instance_id).all()

    async def mark_task_ready(self, task_id: UUID) -> Task:
        """Transitions state PENDING/RETRYING -> READY (Prerequisites met)."""
        task = await self.get_task_by_id(task_id)
        task.mark_ready()

        self._log_event(task.workflow_instance_id, task.id, "TaskReady", {})
        self.db.commit()
        self.db.refresh(task)
        return task

    async def start_task(self, task_id: UUID, assigned_agent_id: Optional[UUID] = None) -> Task:
        """Transitions state READY -> RUNNING."""
        task = await self.get_task_by_id(task_id)

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

    async def complete_task(self, task_id: UUID, output_data: dict = {}) -> Task:
        """Transitions state RUNNING -> COMPLETED."""
        task = await self.get_task_by_id(task_id)

        # Guarded transition
        task.complete(output_data=output_data)

        self._log_event(task.workflow_instance_id, task.id, "TaskCompleted", {"output": output_data})
        self.db.commit()
        self.db.refresh(task)
        return task

    async def fail_task(self, task_id: UUID, error_details: dict = {}) -> Task:
        """Transitions state RUNNING -> FAILED."""
        task = await self.get_task_by_id(task_id)

        # Guarded transition
        task.fail(error_details=error_details)

        self._log_event(task.workflow_instance_id, task.id, "TaskFailed", {"error": error_details})
        self.db.commit()
        self.db.refresh(task)
        return task

    async def retry_task(self, task_id: UUID) -> Task:
        """Transitions state FAILED -> RETRYING."""
        task = await self.get_task_by_id(task_id)

        # Domain method checks if retry_count < max_retries and status is FAILED
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

    async def cancel_task(self, task_id: UUID, reason: str = "Cancelled by user") -> Task:
        """Transitions state PENDING/READY/RUNNING -> CANCELLED."""
        task = await self.get_task_by_id(task_id)

        # Guarded transition
        task.cancel(reason=reason)

        self._log_event(task.workflow_instance_id, task.id, "TaskCancelled", {"reason": reason})
        self.db.commit()
        self.db.refresh(task)
        return task

    async def request_approval(
            self,
            task_id: UUID,
            required_approvers: list = [],
            details: dict = {}
    ) -> Task:
        """Puts a task into RUNNING state while waiting for external human approval."""
        task = await self.get_task_by_id(task_id)

        # Ensure task is transitioned to RUNNING if it was READY
        if task.status == TaskStatus.READY:
            task.start()

        payload = {"approvers": required_approvers, "details": details}
        self._log_event(task.workflow_instance_id, task.id, "ApprovalRequested", payload)

        self.db.commit()
        self.db.refresh(task)
        return task

    async def receive_approval(
            self,
            task_id: UUID,
            approved_by: str,
            approval_metadata: dict = {}
    ) -> Task:
        """Records an approval decision for a running approval task."""
        task = await self.get_task_by_id(task_id)

        if task.status != TaskStatus.RUNNING:
            raise InvalidStateTransitionError("Task", str(task.id), task.status.value, "receive_approval")

        payload = {"approved_by": approved_by, "metadata": approval_metadata}
        self._log_event(task.workflow_instance_id, task.id, "ApprovalReceived", payload)

        self.db.commit()
        self.db.refresh(task)
        return task