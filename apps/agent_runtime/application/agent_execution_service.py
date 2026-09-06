from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.application.agent_registry import AgentRegistry
from apps.agent_runtime.domain.agent_contract import AgentResult, AgentContext, AgentExecutionStatus
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.agent_repository import AgentRepository
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository


class AgentExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.run_repo = AgentRunsRepository(db)
        self.registry = AgentRegistry(self.agent_repo)

    def execute_run(self, run_id : UUID)-> AgentResult:
        """
        Executes a single AgentRun by ID and updates status to "RUNNING"
        It also invokes agent, updates db record to "COMPLETED" or "FAILED", and retruns result.
        """
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise ValueError(f"AgentRun with ID '{run_id}' not found.")

        agent_record = self.agent_repo.get_by_id(run.agent_id)
        if not agent_record:
            raise ValueError(f"Associated Agent with ID '{run.agent_id}' not found.")

        self.run_repo.mark_running(run_id)
        self.db.commit()

        context = AgentContext(
            run_id=run.id,
            agent_id=run.agent_id,
            task_id=run.task_id,
            workflow_instance_id=run.workflow_instance_id,
            input_data=run.input_data or {},
            configuration=agent_record.configuration or {},
        )

        try:
            agent_instance = self.registry.resolve(agent_record.slug)
            result : AgentResult = agent_instance.execute(context)

            if result.status == AgentExecutionStatus.COMPLETED:
                self.run_repo.mark_completed(
                    run_id=run_id,
                    output_data = result.output_data or {}
                )
            else:
                error_dict = {
                    "code": result.error.code if result.error else "UNKNOWN_ERROR",
                    "message": result.error.message if result.error else "Execution failed",
                    "retryable": result.error.retryable if result.error else False,
                }
                self.run_repo.mark_failed(run_id= run_id, error_data=error_dict)
            self.db.commit()
            return result
        except Exception as exc:
            logger.error("Unexpected execution error", run_id=str(run_id), error=str(exc))
            error_dict = {
                "code": "UNHANDLED_EXCEPTION",
                "message": str(exc),
                "retryable": False,
            }
            self.run_repo.mark_failed(run_id=run_id, error_data=error_dict)
            self.db.commit()

            return AgentResult(
                status=AgentExecutionStatus.FAILED,
                error=None,
                execution_duration_ms=0.0
            )