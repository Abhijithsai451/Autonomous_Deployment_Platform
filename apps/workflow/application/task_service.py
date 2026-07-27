from datetime import datetime
from fastapi import HTTPException
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from apps.workflow.domain.tasks import Task, TaskStatus
from apps.workflow.domain.workflow_events import WorkflowEvent
from infrastructure.nats.nats_client import EventBus


class TaskService:
    def __init__(self, db:Session):
        self.db = db

    async def _log_event(self, instance_id: UUID, task_id: UUID, event_type: str, payload: dict):
        event = WorkflowEvent(
            workflow_instance_id=instance_id,
            task_id=task_id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(event)
        self.db.commit()

    async def get_task_by_id(self, task_id: UUID) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found with id {task_id}")
        return task

    async def get_tasks_by_instance(self, instance_id: UUID) -> List[Task]:
        return self.db.query(Task).filter(Task.workflow_instance_id == instance_id).all()

    async def retry_task(self, task_id: UUID) -> Task:
        task = await self.get_task_by_id(task_id)
        if task.status != TaskStatus.FAILED:
            raise HTTPException(status_code=400, detail="Only failed tasks can be retried.")

        task.status = TaskStatus.READY
        task.retry_count += 1
        task.error_details = None
        self.db.commit()

        await self._log_event(task.workflow_instance_id, task.id, "TaskRetried", {"retry_count": task.retry_count})
        await EventBus.publish("TaskStarted", {"task_id": str(task.id), "retry_count": task.retry_count})
        return task

    async def cancel_task(self, task_id: UUID) -> Task:
        task = await self.get_task_by_id(task_id)
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        self.db.commit()

        await self._log_event(task.workflow_instance_id, task.id, "TaskCancelled", {})
        await EventBus.publish("TaskFailed", {"task_id": str(task.id), "reason": "Cancelled by user"})
        return task

    async def complete_task(self, task_id: UUID, output_data: dict = {}) -> Task:
        """Publishes TaskCompleted"""
        task = await self.get_task_by_id(task_id)
        task.status = TaskStatus.COMPLETED
        task.output_data = output_data
        task.completed_at = datetime.utcnow()
        self.db.commit()

        await self._log_event(task.workflow_instance_id, task.id, "TaskCompleted", {"output": output_data})
        await EventBus.publish("TaskCompleted", {"task_id": str(task.id), "instance_id": str(task.workflow_instance_id),
                                                 "output": output_data})
        return task

    async def request_approval(self, task_id: UUID, required_approvers: list = [], details: dict = {}) -> Task:
        """Publishes ApprovalRequested"""
        task = await self.get_task_by_id(task_id)
        task.status = TaskStatus.RUNNING  # Waiting state
        self.db.commit()

        payload = {"approvers": required_approvers, "details": details}
        await self._log_event(task.workflow_instance_id, task.id, "ApprovalRequested", payload)
        await EventBus.publish("ApprovalRequested",
                               {"task_id": str(task.id), "instance_id": str(task.workflow_instance_id), **payload})
        return task

    async def receive_approval(self, task_id: UUID, approved_by: str, approval_metadata: dict = {}) -> Task:
        """Publishes ApprovalReceived"""
        task = await self.get_task_by_id(task_id)
        payload = {"approved_by": approved_by, "metadata": approval_metadata}

        await self._log_event(task.workflow_instance_id, task.id, "ApprovalReceived", payload)
        await EventBus.publish("ApprovalReceived",
                               {"task_id": str(task.id), "instance_id": str(task.workflow_instance_id), **payload})
        return task
