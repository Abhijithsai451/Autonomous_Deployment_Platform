import asyncio
from datetime import datetime, timezone
import os
from typing import Any, Dict, Optional
from uuid import UUID
from opentelemetry import trace

from sqlalchemy.orm import Session

from apps.agent_runtime.agents.agent_orchestrator import Orchestrator
from apps.agent_runtime.domain.agent_contract import AgentExecutionStatus, AgentContext
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.llm.llm_agent import ReActLLMAgent
from apps.agent_runtime.llm.openai_client import OpenAILLMClient
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository
from apps.agent_runtime.repository.outbox_repository import OutboxRepository
from apps.agent_runtime.repository.processed_events_repository import ProcessedEventsRepository

CONSUMER_GROUP = "agent-runtime-task-consumer"
tracer = trace.get_tracer("agent-runtime-handlers")

def handle_task_ready_event(
    db: Session,
    payload: Dict[str, Any],
    metadata: Dict[str, Any],
    api_key: Optional[str] = None
) -> bool:
    """
    Consumes workflow.events.task.ready events, executes the ReAct LLM Agent loop,
    persists run execution state, and stages outbox events.
    """
    event_id_str = str(payload.get("event_id"))
    with tracer.start_as_current_span("handle_task_ready_event") as span:
        span.set_attribute("event.id", event_id_str)
        try:
            event_id = UUID(payload["event_id"])
            task_id = UUID(payload["task_id"])
            workflow_instance_id = UUID(payload["workflow_instance_id"])
            agent_id = UUID(payload.get("agent_id", str(task_id)))

            processed_repo = ProcessedEventsRepository(db)

            # 1. Idempotency Check
            if processed_repo.is_processed(event_id=event_id, consumer_group=CONSUMER_GROUP):
                logger.info("Event already processed, skipping execution", event_id=str(event_id))
                return True

            run_repo = AgentRunsRepository(db)
            outbox_repo = OutboxRepository(db)
            effective_api_key = api_key or os.getenv("OPENAI_API_KEY", "mock-key")

            # 2. Create Initial AgentRun Record (Fixed: use .create instead of .create_run)
            agent_run = run_repo.create(
                task_id=task_id,
                agent_id=agent_id,
                workflow_instance_id=workflow_instance_id,
                input_data=payload.get("input_data", {}),
            )

            run_repo.mark_running(agent_run.id)
            db.commit()

            context = AgentContext(
                run_id=agent_run.id,
                agent_id=agent_id,
                task_id=task_id,
                workflow_instance_id=workflow_instance_id,
                input_data=payload.get("input_data", {}),
                configuration=payload.get("configuration", {}),
            )

            llm_client = OpenAILLMClient(api_key=effective_api_key)
            agent = ReActLLMAgent(llm_client=llm_client, max_iterations=5)

            # 3. Execute Async ReAct Loop Safely
            start_time = datetime.now(timezone.utc)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                agent_result = loop.run_until_complete(agent.execute_async(context))
            else:
                agent_result = asyncio.run(agent.execute_async(context))

            execution_duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # 4. Persist State Based on Agent Result
            error_dict = None
            if agent_result.status == AgentExecutionStatus.COMPLETED:
                run_repo.mark_completed(
                    run_id=agent_run.id,
                    output_data=agent_result.output_data or {},
                    duration_ms = execution_duration_ms
                )
            else:
                error_dict = {
                    "code": agent_result.error.code if agent_result.error else "EXECUTION_FAILED",
                    "message": agent_result.error.message if agent_result.error else "Unknown execution error",
                }
                run_repo.mark_failed(
                    run_id=agent_run.id,
                    error=error_dict,
                    duration_ms = execution_duration_ms
                )

            # 5. Stage Outbox Event & Record Idempotency Entry
            outbox_payload = {
                "run_id": str(agent_run.id),
                "task_id": str(task_id),
                "workflow_instance_id": str(workflow_instance_id),
                "status": agent_result.status.value,
                "output_data": agent_result.output_data,
                "error": error_dict,
            }

            outbox_repo.create_event(
                aggregate_type="AgentRun",
                aggregate_id=agent_run.id,
                event_type="agent_runtime.events.agent.finished",
                payload=outbox_payload,
            )

            processed_repo.mark_processed(
                event_id=event_id,
                consumer_group=CONSUMER_GROUP,
            )

            db.commit()
            logger.info(
                "Agent execution finalized",
                run_id=str(agent_run.id),
                status=agent_result.status.value,
                duration_ms=execution_duration_ms,
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error("Unhandled Exception in the task event Handler", error=str(e), event_id = payload.get("event_id"))
            return False