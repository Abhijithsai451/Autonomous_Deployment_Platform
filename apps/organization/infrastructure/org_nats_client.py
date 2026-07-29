from typing import Callable, Awaitable, Dict, Any
from apps.organization.infrastructure.structured_logs import struct_logger as logger
from infrastructure.nats.nats_client import EventBus

ORGANIZATION_STREAM = "organization_events"
ORGANIZATION_SUBJECT_PREFIX = "organization.events"

class OrganizationNatsEngine:

    async def initialize(self) -> None:
        await EventBus.initialize()
        await EventBus.ensure_stream( stream_name=ORGANIZATION_STREAM, subjects=["organization.>"])
        logger.info(f"Organization NATS publisher initialized on stream '{ORGANIZATION_STREAM}'.")

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if not EventBus._publisher:
            await self.initialize()
        else:
            await EventBus.ensure_stream(stream_name=ORGANIZATION_STREAM, subjects=["organization.>"])
        subject = (
            event_type if event_type.startswith("organization.")
            else f"{ORGANIZATION_SUBJECT_PREFIX}.{event_type}"
        )

        await EventBus.publish(subject=subject,payload=payload,event_type=event_type)

    async def register_listener(self,subject: str,durable_name: str,handler:
    Callable[[dict, dict], Awaitable[None]]) -> None:
        full_subject = (
            subject if subject.startswith("organization.")
            else f"organization.{subject}"
        )

        await EventBus.register_listener(
            stream=ORGANIZATION_STREAM,
            subject=full_subject,
            durable_name=durable_name,
            handler=handler
        )

    async def shutdown(self) -> None:
        await EventBus.shutdown()


org_nats_client = OrganizationNatsEngine()