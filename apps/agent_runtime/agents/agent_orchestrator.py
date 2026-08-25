from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from apps.agent_runtime.application.agent_execution_service import AgentExecutionService
from apps.agent_runtime.domain.agent_contract import AgentExecutionStatus
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.agent_repository import AgentRepository
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository
from apps.agent_runtime.repository.outbox_repository import OutboxRepository


class Orchestrator:
    def __init__(self, db:Session):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.run_repo = AgentRunsRepository(db)
        self.run_repo = OutboxRepository(db)
        self.execution_service = AgentExecutionService(db)

    def process_task(self, task_id: UUID, workflow_instance_id: UUID, agent_slug: str, input_data: Dict[str, Any])-> None:
        """
        Orchestrates the task execution. Resolves Agent, creates run record, executes task and emits outbox events
        inside a single transaction.
        """
        agent = self.agent_repo.get_by_slug(agent_slug)
        if not agent:
            raise ValueError(f"Agent with slug id {agent_slug} not found in database. ")

        existing_run = self.run_repo.get_by_id(task_id)
        if existing_run:
            logger.info(f"Agent Run already exists for the task_id: {str(task_id)} in the database. ")
            run = existing_run
        else:
            run = self.run_repo.create(
                agent_id = agent.id,
                task_id = task_id,
                workflow_instance_id=workflow_instance_id,
                input_data=input_data
            )

        result = self.execution_service.execute_run(run.id)

        event_type = (
            "agent_runtime.events.agent.finished"
            if result.status == AgentExecutionStatus.COMPLETED
            else "agent_runtime.events.agent.failed"
        )
        payload = {
            "event_id": str(uuid4()),
            "agent_run_id": str(run.id),
            "task_id": str(task_id),
            "workflow_instance_id": str(workflow_instance_id),
            "agent_id": str(agent.id),
            "status": result.status.value,
            "output_data": result.output_data or {},
            "error": {
                "code": result.error.code,
                "message": result.error.message
            } if result.error else {}
        }

        self.outbox_repo.create(
            event_type=event_type,
            aggregate_type="AGENT_RUN",
            aggregate_id=run.id,
            payload=payload
        )

        self.db.commit()