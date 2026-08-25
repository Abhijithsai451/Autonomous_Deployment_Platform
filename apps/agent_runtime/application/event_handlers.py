from typing import Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.agents.agent_orchestrator import Orchestrator
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.processed_events_repository import ProcessedEventsRepository

CONSUMER_GROUP = "agent-runtime-task-consumer"

def handle_task_ready_event(db:Session, payload: Dict[str,Any], metadata: Dict[str, Any])-> bool:
    """
    Handles workflow task event idempotently
    Returns True if processed Successfully or ignored as duplicate
    """
    event_id_str = metadata.get("event_id") or payload.get("event_id")
    if not event_id_str:
        logger.error("Missing event_id in the payload or metadata")
        return False

    event_id = UUID(event_id_str)
    processed_repo = ProcessedEventsRepository(db)

    if processed_repo.is_processed(event_id):
        logger.info("Duplicate Event and is Ignored", event_id = event_id_str, consumer_group=CONSUMER_GROUP )
        return True

    try:
        task_id = UUID(payload["task_id"])
        workflow_instance_id = UUID(payload["workflow_instance_id"])
        agent_slug = payload.get("agent_slug", "test-agent-1")
        input_data = payload.get("input_data", {})

        orchestrator = Orchestrator(db)
        orchestrator.process_task(
            task_id = task_id,
            workflow_instance_id=workflow_instance_id,
            agent_slug=agent_slug,
            input_data=input_data,
        )
        processed_repo.mark_processed(event_id, CONSUMER_GROUP)
        db.commit()
        logger.info("Successfully processed task event", event_id= str(event_id), task_id= str(task_id))
        return True,
    except Exception as e:
        db.rollback()
        logger.error("Failed to process the task ready event",event_id= str(event_id),error = str(e) )
        raise e
