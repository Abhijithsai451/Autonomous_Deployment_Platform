from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.workflow.domain.outbox import OutboxEvent
from apps.workflow.domain.task_dependencies import TaskDependency
from apps.workflow.domain.tasks import TaskStatus, Task
from apps.workflow.domain.workflow_events import WorkflowEvent
from apps.workflow.infrastructure.structured_logs import struct_logger as logger


class TaskDependencyEngine:
    """
    Evaluates and updates task dependency state graphs (DAGs) within an active database transaction.
    """
    def __init__(self, db: Session):
        self.db = db

    def evaluate_downstream_tasks(self, completed_task: Task) -> List[Task]:
        dep_stmt = select(TaskDependency.task_id).where(
            TaskDependency.depends_on_task_id == completed_task.id
        )
        child_task_ids = self.db.scalars(dep_stmt).all()

        if not child_task_ids:
            logger.debug(f"Task {completed_task.id} has no downstream dependencies.")
            return []

        children_stmt = select(Task).where(
            Task.id.in_(child_task_ids),
            Task.status == TaskStatus.PENDING
        )
        pending_children = self.db.scalars(children_stmt).all()

        unlocked_tasks: List[Task] = []

        for child in pending_children:
            if self._are_all_dependencies_completed(child.id):
                child.status = TaskStatus.READY
                unlocked_tasks.append(child)
                self._stage_unlocked_events(child)
                logger.info(f"Task {child.id} ({child.name}) unlocked -> status set to READY")

        return unlocked_tasks

    def cascade_failure(self, failed_task: Task) -> List[Task]:
        """
        Called when a task enters FAILED or CANCELLED status.
        Recursively cancels downstream pending tasks that can no longer run.
        """
        dep_stmt = select(TaskDependency.task_id).where(
            TaskDependency.depends_on_task_id == failed_task.id
        )
        child_task_ids = self.db.scalars(dep_stmt).all()

        if not child_task_ids:
            return []

        children_stmt = select(Task).where(
            Task.id.in_(child_task_ids),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.READY])
        )
        affected_children = self.db.scalars(children_stmt).all()
        cancelled_tasks: List[Task] = []

        for child in affected_children:
            child.status = TaskStatus.CANCELLED
            child.error_details = {
                "reason": f"Upstream dependency failed/cancelled: task_id={failed_task.id}"
            }
            cancelled_tasks.append(child)
            self._stage_cancellation_events(child)
            logger.warning(f"Task {child.id} ({child.name}) cancelled due to upstream failure.")

            # Recursively cascade to child's children
            cancelled_tasks.extend(self.cascade_failure(child))

        return cancelled_tasks

    def _are_all_dependencies_completed(self, task_id: UUID) -> bool:
        """
        Checks if every upstream task for a given task_id is COMPLETED.
        """
        stmt = (
            select(Task.status)
            .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
            .where(TaskDependency.task_id == task_id)
        )
        parent_statuses = self.db.scalars(stmt).all()

        return all(status == TaskStatus.COMPLETED for status in parent_statuses)

    def _stage_unlocked_events(self, task: Task) -> None:
        """
        Stages audit and outbox records for a task transitioning to READY.
        """
        payload = {
            "task_id": str(task.id),
            "workflow_instance_id": str(task.workflow_instance_id),
            "action_type": task.action_type,
            "status": task.status.value,
        }

        # Audit Event
        self.db.add(WorkflowEvent(
            workflow_instance_id=task.workflow_instance_id,
            task_id=task.id,
            event_type="TaskReady",
            payload=payload
        ))

        # Outbox Event
        self.db.add(OutboxEvent(
            event_type="workflow.events.TaskReady",
            aggregate_type="Task",
            aggregate_id=task.id,
            payload=payload
        ))

    def _stage_cancellation_events(self, task: Task) -> None:
        """
        Stages audit and outbox records for a cancelled task.
        """
        payload = {
            "task_id": str(task.id),
            "workflow_instance_id": str(task.workflow_instance_id),
            "status": task.status.value,
            "error_details": task.error_details
        }

        self.db.add(WorkflowEvent(
            workflow_instance_id=task.workflow_instance_id,
            task_id=task.id,
            event_type="TaskCancelled",
            payload=payload
        ))

        self.db.add(OutboxEvent(
            event_type="workflow.events.TaskCancelled",
            aggregate_type="Task",
            aggregate_id=task.id,
            payload=payload
        ))