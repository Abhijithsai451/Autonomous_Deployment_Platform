from typing import Optional, Any, Dict, Callable, Awaitable

from infrastructure.nats.nats_client import NatsClient
from infrastructure.nats.publisher import Publisher
from infrastructure.nats.subscriber import Subscriber
from packages.config.settings import common_settings
from packages.events.base import BaseEvent
from packages.events.event_envelope import EventEnvelope
from packages.logging.structured_logs import struc_logger as logger

class EventBus:
    def __init__(self, service: str, nats_url: Optional[str]=None):
        self.service = service.lower()
        self.stream_name = f"{self.service}_events"
        self.subject_prefix = f"{self.service}.events"

        self.client = NatsClient(nats_url= nats_url or common_settings.NATS_URL)
        self.publisher = Publisher(self.client)
        self.subscriber = Subscriber(self.client)

    async def initialize(self)-> None:
        # Connects to the NATS Client
        await self.client.connect()
        await self.client.ensure_stream(
            stream_name = self.stream_name,
            subjects = [f"{self.service}.>"]
        )
        logger.info(f"EventBus initialized for service '{self.service}'.")
    async def publish(self, event_type: str, payload: Dict[str, Any])-> None:
        # Calls the publisher.publish function to send a message.
        subject= (
            event_type if event_type.startswith(f"{self.service}.")
            else f"{self.subject_prefix}.{event_type}"
        )
        await self.publisher.publish(
            subject=subject,
            payload=payload,
            event_type = event_type
        )

    async def publish_event(self, event: BaseEvent)-> None:
        """Publishes a typed BaseEvent wrapped automatically in an EventEnvelope"""
        envelope = EventEnvelope.wrap(event = event, source_service = self.service)
        await self.publisher.publish(
            subject = event.subject,
            payload = envelope.model_dump(model="json"),
            event_type = event.event_name,
            idempotency_key = str(event.event_id)
        )

    async def register_listener(self,
                                subject: str,
                                durable_name: str,
                                handler: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]],
                                stream: str = None
                                ) -> None:
        full_subject = (
            subject if "." in subject else f"{self.subject_prefix}.{subject}"
        )
        await self.subscriber.subscribe(
            stream=stream,
            subject=full_subject,
            durable_name=durable_name,
            handler=handler
        )

    async def shutdown(self) -> None:
        if hasattr(self.subscriber, "unsubscribe_all"):
            await self.subscriber.unsubscribe_all()
        await self.client.close()

