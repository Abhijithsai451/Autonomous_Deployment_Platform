from typing import Callable, Awaitable, Dict, Any

from apps.workflow.infrastructure.structured_logs import struct_logger as logger
from infrastructure.nats.nats_client import EventBus



WORKFLOW_STREAM = "workflow_events"
WORKFLOW_SUBJECT_PREFIX = "workflow.events"

class WorkflowNatsEngine:
    async def initialize(self) -> None:

        await EventBus.initialize()
        await EventBus.ensure_stream(
            stream_name=WORKFLOW_STREAM,
            subjects=["workflow.*"]
        )
        logger.info(f"Workflow NATS publisher initialized on stream '{WORKFLOW_STREAM}'.")

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        subject = (
            event_type if event_type.startswith("workflow.")
            else f"{WORKFLOW_SUBJECT_PREFIX}.{event_type}"
        )

        await EventBus.publish(
            subject=subject,
            payload=payload,
            event_type=event_type
        )

    async def register_listener(
            self,
            subject: str,
            durable_name: str,
            handler: Callable[[dict, dict], Awaitable[None]]
    ) -> None:
        full_subject = (
            subject if subject.startswith("workflow.")
            else f"workflow.{subject}"
        )

        await EventBus.register_listener(
            stream=WORKFLOW_STREAM,
            subject=full_subject,
            durable_name=durable_name,
            handler=handler
        )

    async def shutdown(self) -> None:
        await EventBus.shutdown()

workflow_nats_client = WorkflowNatsEngine()