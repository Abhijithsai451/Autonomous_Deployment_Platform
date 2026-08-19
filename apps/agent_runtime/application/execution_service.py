import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent_runtime.agents.echo_agent import EchoAgent
from apps.agent_runtime.domain.agent_runs import AgentRuns
from apps.agent_runtime.domain.agents import Agent, AgentStatus, RunStatus
from apps.agent_runtime.domain.outbox import OutboxEvent, OutboxStatus
from apps.agent_runtime.domain.processed_event import ProcessedEvent


class ExecutionService:

    @staticmethod
    async def process_event(db: Session, payload: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        headers = metadata.get("headers", {})
        raw_event_id = payload.get("event_id") or headers.get("Nats-Msg-Id") or str(uuid.uuid4())
        event_id = uuid.UUID(str(raw_event_id))
        consumer_group = "agent-runtime-task-ready-consumer"

        existing_processed = db.execute(
            select(ProcessedEvent).where(
                ProcessedEvent.event_id == event_id,
                ProcessedEvent.consumer_group == consumer_group
            )
        ).scalar_one_or_none()

        if existing_processed:
            return

        task_id = uuid.UUID(str(payload["task_id"]))
        workflow_instance_id = uuid.UUID(str(payload["workflow_instance_id"]))
        input_data = payload.get("input_data") or payload.get("payload") or {}
        agent_slug = payload.get("agent_slug", "test-agent-1")

        agent = db.execute(select(Agent).where(Agent.slug == agent_slug)).scalar_one_or_none()
        if not agent:
            agent = db.execute(select(Agent).where(Agent.status == AgentStatus.ACTIVE)).scalars().first()

        if not agent:
            raise ValueError("No active agent available to execute task")

        agent_run = AgentRuns(
            agent_id=agent.id,
            task_id=task_id,
            workflow_instance_id=workflow_instance_id,
            status=RunStatus.RUNNING,
            input_data=input_data,
            started_at=datetime.now(timezone.utc)
        )
        db.add(agent_run)
        db.flush()

        executor = EchoAgent()
        output_data = await executor.run(agent, input_data)

        agent_run.status = RunStatus.COMPLETED
        agent_run.output_data = output_data
        agent_run.completed_at = datetime.now(timezone.utc)

        db.add(ProcessedEvent(event_id=event_id, consumer_group=consumer_group))

        outbox_entry = OutboxEvent(
            event_type="agent.run.completed",
            aggregate_type="AGENT_RUN",
            aggregate_id=agent_run.id,
            payload={
                "agent_run_id": str(agent_run.id),
                "task_id": str(task_id),
                "workflow_instance_id": str(workflow_instance_id),
                "status": agent_run.status.value,
                "output_data": agent_run.output_data
            },
            status=OutboxStatus.PENDING
        )
        db.add(outbox_entry)

        db.commit()