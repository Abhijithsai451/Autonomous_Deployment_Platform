import uuid
import logging
from enum import Enum
from typing import Dict, Any, Callable, Awaitable, List, Optional

from packages.config.settings import common_settings as settings
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

        if cls._subscriber is None:
            cls._subscriber = Subscriber(nats_url=settings.NATS_URL)
            await cls._subscriber.connect()

    @classmethod
    async def ensure_stream(cls, stream_name: str, subjects: List[str]):
        if not cls._publisher:
            await cls.initialize()
        try:
            await cls._publisher.js.add_stream(name=stream_name, subjects=subjects)
            logger.info(f"JetStream stream '{stream_name}' ensured for subjects {subjects}")
        except Exception as err:
            logger.debug(f"Stream '{stream_name}' already exists or notice: {err}")

    @classmethod
    async def publish(
            cls,
            subject: str,
            payload: Dict[str, Any],
            event_type: Optional[str] = None
    ):

        if not cls._publisher:
            await cls.initialize()

        if isinstance(event_type, Enum):
            event_name = event_type.name
        elif event_type:
            event_name = str(event_type)
        else:
            event_name = subject.split(".")[-1]

        idempotency_key = str(uuid.uuid4())

        await cls._publisher.publish_event(
            subject=subject,
            event_type=event_name,
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
        if cls._publisher:
            await cls._publisher.close()
            cls._publisher = None
        if cls._subscriber:
            await cls._subscriber.close()
            cls._subscriber = None