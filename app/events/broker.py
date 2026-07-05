import json

from app.core.providers import AppConfig
from nats.aio.client import Client as NATS

class EventBroker:
    def __init__(self, config: AppConfig):
        self.config = config
        self.nc = NATS()
        self.js = None

    async def connect(self):
        await self.nc.connect("nats://localhost:4222")
        self.js = self.nc.jetstream()

        await self.js.add_stream(name="cortexops_events", subjects= ["cortexops.*"])

    async def publish(self, subject:str, payload:dict):
        if not self.js:
            raise RuntimeError("Events broker is not connected to Jetstream")

        bytes_data = json.dump(payload).encode("utf-8")
        await self.js.publish(subject, bytes_data)

    async def close(self):
        if self.nc.is_connected():
            await self.nc.drain()

