from typing import Callable, Awaitable, Dict, Any

from apps.identity.infrastructure.structured_logs import struct_logger as logger
from infrastructure.nats.nats_client import EventBus

IDENTITY_STREAM = "identity_events"
IDENTITY_SUBJECT_PREFIX = "identity.events"

class IdentityNatsEngine:

    async def initialize(self) -> None:
        await EventBus.initialize()
        await EventBus.ensure_stream( stream_name=IDENTITY_STREAM, subjects=["identity.>"])
        logger.info(f"Identity NATS publisher initialized on stream '{IDENTITY_STREAM}'.")

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if not EventBus._publisher:
            await self.initialize()
        else:
            await EventBus.ensure_stream(stream_name=IDENTITY_STREAM, subjects=["identity.>"])
        subject = (
            event_type if event_type.startswith("identity.")
            else f"{IDENTITY_SUBJECT_PREFIX}.{event_type}"
        )

        await EventBus.publish(subject=subject,payload=payload,event_type=event_type)

    async def register_listener(self,subject: str,durable_name: str,handler:
    Callable[[dict, dict], Awaitable[None]]) -> None:
        full_subject = (
            subject if subject.startswith("identity.")
            else f"identity.{subject}"
        )

        await EventBus.register_listener(
            stream=IDENTITY_STREAM,
            subject=full_subject,
            durable_name=durable_name,
            handler=handler
        )

    async def shutdown(self) -> None:
        await EventBus.shutdown()


identity_nats_client = IdentityNatsEngine()