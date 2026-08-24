from datetime import timezone, datetime
from typing import Any, Optional, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.domain.agent_runs import AgentRuns


class AgentRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, agent_id: UUID, task_id : UUID, workflow_instance_id: UUID,
               input_data: dict[str, Any])-> AgentRuns:
        run = AgentRuns(
            agent_id = agent_id,
            task_id = task_id,
            workflow_instance_id = workflow_instance_id,
            status = "PENDING",
            input_data = input_data,
            created_at= datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> Optional[AgentRuns]:
        return self.db.query(AgentRuns).filter(AgentRuns.id == run_id).first()

    def get_by_task_id(self, task_id: UUID) -> Optional[AgentRuns]:
        return self.db.query(AgentRuns).filter(AgentRuns.task_id == task_id).first()

    def mark_running(self, run_id: UUID) -> Optional[AgentRuns]:
        run = self.get_by_id(run_id)
        if run:
            run.status = "RUNNING"
            run.started_at = datetime.now(timezone.utc)
            self.db.flush()
        return run

    def mark_completed(self, run_id: UUID, output_data: Dict[str, Any]) -> Optional[AgentRuns]:
        run = self.get_by_id(run_id)
        if run:
            run.status = "COMPLETED"
            run.output_data = output_data
            run.completed_at = datetime.now(timezone.utc)
            self.db.flush()
        return run

    def mark_failed(self, run_id: UUID, error_data: Dict[str, Any]) -> Optional[AgentRuns]:
        run = self.get_by_id(run_id)
        if run:
            run.status = "FAILED"
            run.error = error_data
            run.completed_at = datetime.now(timezone.utc)
            self.db.flush()
        return run
