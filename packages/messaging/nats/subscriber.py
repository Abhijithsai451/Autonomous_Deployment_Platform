import json
from typing import Callable, Dict, Any, Awaitable, Type

from nats.js.api import ConsumerConfig, DeliverPolicy

from packages.messaging.nats.nats_client import NatsClient
from packages.events.base import BaseEvent
from packages.events.context import RequestContext
from packages.events.serializer import EventSerializer
from packages.logging.structured_logs import struc_logger as logger
from packages.telemetry.nats import extract_nats_headers
from opentelemetry import trace

tracer = trace.get_tracer("cortexops-nats-subscriber")
class Subscriber:
    def __init__(self, client: NatsClient):
        self.client = client
        self._subscriptions = []
        self._event_handlers : Dict[Type[BaseEvent], Callable[[BaseEvent], Awaitable[None]]] = {}

    def register_handler(self,event_cls: Type[BaseEvent],handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        self._event_handlers[event_cls] = handler

    def on_event(self, event_cls: Type[BaseEvent]):
        def decorator(func: Callable[[BaseEvent], Awaitable[None]]):
            self.register_handler(event_cls, func)
            return func
        return decorator

    async def subscribe(
        self,
        stream: str,
        subject: str,
        durable_name: str,
        handler: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]],
        max_deliver: int = 3
    ) -> None:
        if not self.client.js:
            await self.client.connect()

        config = ConsumerConfig(
            durable_name=durable_name,
            deliver_policy=DeliverPolicy.ALL,
            max_deliver=max_deliver,
            ack_wait = 10,
        )

        async def _msg_handler(msg):
            msg_headers = dict(msg.headers) if msg.headers else {}
            parent_ctx = extract_nats_headers(msg_headers)

            with tracer.start_as_current_span(f"nats.consume.{subject}", context=parent_ctx):
                try:
                    if handler is None:
                        typed_event, envelope = EventSerializer.deserialize_event(msg.data)
                        RequestContext.set(
                            correlation_id=envelope.correlation_id,
                            tenant_id=envelope.tenant_id,
                            causation_id=envelope.message_id
                        )

                        registered_handler = self._event_handlers.get(type(typed_event))
                        if registered_handler:
                            await registered_handler(typed_event)
                        else:
                            logger.warning(f"No handler registered for typed event '{typed_event.event_name}'")
                    else:
                        raw_payload = json.loads(msg.data.decode("utf-8"))
                        metadata = {
                            "subject": msg.subject,
                            "headers": msg_headers,
                            "reply": msg.reply
                        }
                        await handler(raw_payload, metadata)

                    await msg.ack()

                except Exception as e:
                    metadata = await msg.metadata()

                    if metadata.num_delivered >= max_deliver:
                        logger.error(
                            f"Message on '{subject}' exceeded max redeliveries ({max_deliver}). Routing to DLQ: {e}",
                            exc_info=True
                        )
                        dlq_subject = f"{subject.split('.')[0]}.dlq"
                        await self.client.js.publish(
                            dlq_subject,
                            msg.data,
                            headers={
                                "x-dlq-reason": str(e),
                                "x-original-subject": msg.subject,
                                "x-delivery-count": str(metadata.num_delivered)
                            }
                        )
                        await msg.ack()
                    else:
                        logger.warning(
                            f"Transient failure handling message on '{subject}' (attempt {metadata.num_delivered}/{max_deliver}): {e}"
                        )
                        await msg.nak()

        sub = await self.client.js.subscribe(
            subject=subject,
            durable=durable_name,
            queue=durable_name,
            stream=stream,
            config=config,
            cb=_msg_handler,
            manual_ack=True
        )

        self._subscriptions.append(sub)
        logger.info(f"Subscribed to subject '{subject}' on stream '{stream}' (durable={durable_name})")
    async def unsubscribe_all(self) -> None:
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        self._subscriptions.clear()

