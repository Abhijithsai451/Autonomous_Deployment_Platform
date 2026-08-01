import json
import uuid
from typing import Any, Dict, Optional

from infrastructure.nats.nats_client import NatsClient
from packages.logging.structured_logs import struc_logger as logger


class Publisher:
    def __init__(self, client: NatsClient):
        self.client = client

    async def publish(
        self,
        subject: str,
        payload: Dict[str, Any],
        event_type: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> None:
        if not self.client.js:
            await self.client.connect()

        headers = {
            "Nats-Msg-Id": idempotency_key or str(uuid.uuid4()),
            "event_type": event_type or subject.split(".")[-1]
        }

        data = json.dumps(payload).encode("utf-8")
        ack = await self.client.js.publish(subject, data, headers=headers)
        logger.debug(f"Published to '{subject}' [seq={ack.stream}:{ack.seq}]")