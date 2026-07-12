import uuid
import logging
from typing import Dict, Any, Callable, Awaitable

from packages.config.settings import settings
from packages.messaging.publisher import Publisher
from packages.messaging.subscriber import Subscriber

logger = logging.getLogger("cortexops_sdk.messaging")

class EventBus:
    _publisher = None
    _subscriber = None

    @classmethod
    async def initialize(cls):
        """Initializes both Publisher and Subscriber instances across the app lifecycle."""
        if cls._publisher is None:
            cls._publisher = Publisher(nats_url=settings.NATS_URL)
            await cls._publisher.connect()

            # Ensure the durable core stream exists for identity domain events
            try:
                await cls._publisher.js.add_stream(name="identity_events", subjects=["identity.*"])
            except Exception:
                pass

        if cls._subscriber is None:
            cls._subscriber = Subscriber(nats_url=settings.NATS_URL)
            await cls._subscriber.connect()

    @classmethod
    async def publish(cls, event_type: str, payload: Dict[str, Any]):
        """Wraps the application service event into your exact telemetry-tracked publisher."""
        if not cls._publisher:
            await cls.initialize()

        subject = f"identity.{event_type.lower()}"
        idempotency_key = str(uuid.uuid4())

        await cls._publisher.publish_event(
            subject=subject,
            event_type=event_type,
            payload=payload,
            idempotency_key=idempotency_key
        )

    @classmethod
    async def register_listener(
            cls,
            stream: str,
            subject: str,
            durable_name: str,
            handler: Callable[[dict, dict], Awaitable[None]]
    ):
        """Exposes the EventSubscriber configuration for listening to domestic/foreign domains."""
        if not cls._subscriber:
            await cls.initialize()
        await cls._subscriber.subscribe(
            stream=stream,
            subject=subject,
            durable_name=durable_name,
            handler=handler
        )

    @classmethod
    async def shutdown(cls):
        """Gracefully tears down downstream network channels."""
        if cls._publisher:
            await cls._publisher.close()
        if cls._subscriber:
            await cls._subscriber.close()