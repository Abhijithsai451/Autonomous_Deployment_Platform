import json
import logging
import time
from typing import Dict, Any, Callable, Awaitable

import nats
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from packages.tracing.tracing import inject_trace_context

logger = logging.getLogger("cortexops_sdk.messaging")

class Publisher:
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.js = None

    async def connect(self):
        """Connects to the NATS and initializes the jetstream context"""
        self.nc = await nats.connect(self.nats_url)
        self.js = self.nc.jetstream()

    async def publish_event(self, subject: str, event_type: str, payload: Dict[str, Any], idempotency_key: str):
        """
        Publishes the message to the NATS Serve with structured headers,
        idempotency keys and trace context.
        """
        if not self.js:
            raise RuntimeError("EventBus is not connected, Call connect() first")

        envelope = {
            "metadata": {
                "event_type": event_type,
                "time_stamp": time.time(),
                "idempotency_key": idempotency_key
            },
            "data": payload
        }

        trace_headers = inject_trace_context()

        nats_headers = {
            "Nats-Msg-Id": idempotency_key
        }
        for key, value in trace_headers.items():
            nats_headers[key] = value

        serialized_payload = json.dumps(envelope).encode("utf-8")

        await self.js.publish(
            subject= subject,
            payload = serialized_payload,
            headers= nats_headers
        )

    async def close(self):
        if self.nc:
            await self.nc.close()



