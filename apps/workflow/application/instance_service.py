from datetime import datetime
from fastapi import HTTPException
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from apps.workflow.domain.task_dependencies import TaskDependency
from apps.workflow.domain.tasks import Task, TaskStatus
from apps.workflow.domain.workflow_events import WorkflowEvent
from apps.workflow.domain.workflow_instance import WorkflowInstance, WorkflowStatus
from infrastructure.nats.nats_client import EventBus

class InstanceService:
    def __init__(self, db:Session):
        self.db = db

    async def _log_event(self, instance_id: UUID, event_type: str, payload: dict, task_id: Optional[UUID] = None):
        event = WorkflowEvent(
            workflow_instance_id=instance_id,
            task_id=task_id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(event)
        self.db.commit()

    async def create_instance(self, blueprint_id: UUID, input_data: dict, started_by: Optional[UUID] = None) -> WorkflowInstance:
        instance = WorkflowInstance(
            blueprint_id=blueprint_id,
            status=WorkflowStatus.PENDING,
            input_data=input_data,
            started_by=started_by,
            started_at=datetime.utcnow()
        )
        self.db.add(instance)
        self.db.flush()

        blueprint = instance.blueprint
        if blueprint and "tasks" in blueprint.definition:
            created_tasks = {}
            for task_def in blueprint.definition["tasks"]:
                task = Task(
                    workflow_instance_id=instance.id,
                    task_definition_id=task_def["id"],
                    name=task_def["name"],
                    action_type=task_def.get("action_type", "GENERIC"),
                    status=TaskStatus.PENDING,
                    input_data=task_def.get("input_data", {})
                )
                self.db.add(task)
                self.db.flush()
                created_tasks[task_def["id"]] = task.id
                await EventBus.publish("TaskCreated", {"instance_id": str(instance.id), "task_id": str(task.id)})

            for task_def in blueprint.definition["tasks"]:
                if "depends_on" in task_def:
                    current_task_id = created_tasks[task_def["id"]]
                    for dep_def_id in task_def["depends_on"]:
                        dep_task_id = created_tasks[dep_def_id]
                        dep = TaskDependency(task_id=current_task_id, depends_on_task_id=dep_task_id)
                        self.db.add(dep)
            self.db.commit()

        instance.status = WorkflowStatus.RUNNING
        self.db.commit()

        await self._log_event(instance.id, "WorkflowStarted", {"input": input_data})
        await EventBus.publish("WorkflowStarted", {"id": str(instance.id), "blueprint_id": str(blueprint_id)})
        return instance

    async def start_instance(self, instance_id: UUID) -> WorkflowInstance:
        """
        Triggers execution:
        1. Invokes domain method instance.start() (PENDING -> RUNNING)
        2. Unlocks root tasks (tasks with 0 dependencies) -> READY
        3. Records audit log event
        """
        instance = self.db.query(WorkflowInstance).get(instance_id)
        if not instance:
            raise ValueError(f"WorkflowInstance {instance_id} not found")

        # Guarded transition (PENDING -> RUNNING)
        instance.start()

        # Mark root tasks (tasks without dependencies) as READY
        for task in instance.tasks:
            if not task.dependencies and task.status == TaskStatus.PENDING:
                task.mark_ready()

        self._log_event(instance.id, "WorkflowStarted", {"started_at": str(instance.started_at)})

        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def pause_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.db.query(WorkflowInstance).get(instance_id)
        if not instance:
            raise ValueError(f"WorkflowInstance {instance_id} not found")

        instance.pause()
        self._log_event(instance.id, "WorkflowPaused", {})

        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def resume_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.db.query(WorkflowInstance).get(instance_id)
        if not instance:
            raise ValueError(f"WorkflowInstance {instance_id} not found")

        instance.resume()
        self._log_event(instance.id, "WorkflowResumed", {})

        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def cancel_instance(self, instance_id: UUID, reason: str = "User cancelled execution") -> WorkflowInstance:
        instance = self.db.query(WorkflowInstance).get(instance_id)
        if not instance:
            raise ValueError(f"WorkflowInstance {instance_id} not found")

        instance.cancel(reason=reason)

        # Also cancel all active/pending tasks
        for task in instance.tasks:
            if task.status in {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING}:
                task.cancel(reason=f"Workflow cancelled: {reason}")

        self._log_event(instance.id, "WorkflowCancelled", {"reason": reason})

        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def get_instances(self, limit: int = 100, offset: int = 0) -> List[WorkflowInstance]:
        return self.db.query(WorkflowInstance).offset(offset).limit(limit).all()

    async def get_instance_by_id(self, instance_id: UUID) -> WorkflowInstance:
        instance = self.db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail=f"Workflow instance not found with id {instance_id}")
        return instance

    async def retry_instance(self, instance_id: UUID) -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id)

        # Domain-guarded transition (FAILED -> RUNNING)
        instance.retry()

        self._log_event(instance.id, "WorkflowRetried", {})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def signal_instance(self, instance_id: UUID, signal_name: str, payload: dict) -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id)

        # Audit event logged inside DB session
        self._log_event(instance.id, f"SignalReceived:{signal_name}", payload)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def complete_instance(self, instance_id: UUID, output_data: dict = {}) -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id)

        # Domain-guarded transition (RUNNING -> COMPLETED)
        instance.complete(output_data=output_data)

        self._log_event(instance.id, "WorkflowCompleted", {"output": output_data})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def fail_instance(self, instance_id: UUID, error_details: dict = {}) -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id)

        # Domain-guarded transition (RUNNING -> FAILED)
        instance.fail(error_details=error_details)

        self._log_event(instance.id, "WorkflowFailed", {"error": error_details})
        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def timeout_instance(self, instance_id: UUID, reason: str = "Execution timeout reached") -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id)

        # Domain-guarded transition (RUNNING -> TIMED_OUT)
        instance.timeout(reason=reason)

        self._log_event(instance.id, "WorkflowTimedOut", {"reason": reason})
        self.db.commit()
        self.db.refresh(instance)
        return instance
    async def update_workflow_instance(self, updates: dict):
        pass

    async def update_workflow_instance_status(self, status):
        pass
