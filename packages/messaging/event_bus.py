import json
import logging
import time
from typing import Dict, Any, Callable, Awaitable

import nats
from nats.js.api import Header
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from packages.tracing.tracing import inject_trace_context

logger = logging.getLogger("cortexops_sdk.messaging")

class EventBus:
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

        nats_headers = Header()
        nats_headers["Nats-Msg-Id"] = idempotency_key
        for key, value in trace_headers.items():
            nats_headers[key] = value

        serialized_payload = json.dumps(envelope).encode("utf-8")

        await self.jc.publish(
            subject= subject,
            payload = serialized_payload,
            headers= nats_headers
        )

    async def close(self):
        if self.nc:
            await self.nc.close()

class EventSubscriber:
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.js = None

    async def connect(self):
        """Connects to the NATS and initializes the jetstream context"""
        self.nc = await nats.connect(self.nats_url)
        self.js = self.nc.jetstream()

    async def subscribe(
            self,
            stream: str,
            subject: str,
            durable_name: str,
            handler: Callable[[dict,dict], Awaitable[None]]
            ):
        """
        Subscribes to a JetStream subject, extracts distributed tracing metadata,
        and hands the unpacked payload to a processing function.
        """
        if not self.js:
            raise RuntimeError("EventSubscriber is not connected, Please run the connect() first ")

        try:
            await self.js.add_stream(name= stream, subjects=[subject])
        except Exception:
            pass

        # Define the message processing loop wrapper
        async def message_callback(msg):
            try:
                # 1. Extract OpenTelemetry tracing headers from NATS metadata
                headers = msg.headers or {}
                parent_context = TraceContextTextMapPropagator().extract(carrier=headers)

                # 2. Start a tracer span tied to the publisher's origin trace ID
                tracer = trace.get_tracer("cortexops_subscriber")
                with tracer.start_as_current_span(f"nats.consume.{subject}", context=parent_context):

                    # 3. Decode payload envelope
                    raw_data = json.loads(msg.data.decode("utf-8"))
                    metadata = raw_data.get("metadata", {})
                    payload = raw_data.get("data", {})

                    # 4. Pass decoded data to your service's business logic handler
                    await handler(payload, metadata)

                    # 5. Acknowledge message success back to NATS JetStream
                    await msg.ack()

            except Exception as e:
                logger.error(f"Failed to process message on {subject}: {str(e)}")
                # Tell NATS to retry sending this message shortly
                await msg.nak()

        # Create a durable consumer so if your service restarts, it picks up where it left off
        await self.js.subscribe(
            subject=subject,
            durable=durable_name,
            cb=message_callback,
            manual_ack=True  # Forces manual verification via msg.ack() before discarding
        )


