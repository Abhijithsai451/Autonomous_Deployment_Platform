import json
from typing import Callable, Dict, Any, Awaitable

from infrastructure.nats.nats_client import NatsClient
from packages.logging.structured_logs import struc_logger as logger

class Subscriber:
    def __init__(self, client: NatsClient):
        self.client = client
        self._subscriptions = []
    async def subscribe(
        self,
        stream: str,
        subject: str,
        durable_name: str,
        handler: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]
    ) -> None:
        if not self.client.js:
            await self.client.connect()

        async def _msg_handler(msg):
            try:
                raw_payload = json.loads(msg.data.decode("utf-8"))
                metadata = {
                    "subject": msg.subject,
                    "headers": dict(msg.headers) if msg.headers else {},
                    "reply": msg.reply
                }
                await handler(raw_payload, metadata)
                await msg.ack()
            except Exception as e:
                logger.error(f"Error handling message on subject '{subject}': {e}", exc_info=True)

        await self.client.js.subscribe(
            subject=subject,
            durable=durable_name,
            queue = durable_name,
            stream=stream,
            cb=_msg_handler,
            manual_ack=True
        )
        logger.info(f"Subscribed to subject '{subject}' on stream '{stream}' (durable={durable_name})")

    async def unsubscribe_all(self) -> None:
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        self._subscriptions.clear()

