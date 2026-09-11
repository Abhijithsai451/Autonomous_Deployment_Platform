
from typing import  List, Optional

import nats
from nats.js import JetStreamContext

from packages.logging.structured_logs import struc_logger as logger

class NatsClient:
    """Establishes the NATS Client connection and manages the JetStream context lifecycle."""
    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.nc: Optional[nats.NATS]= None
        self.js : Optional[JetStreamContext] = None

    async def connect(self)-> None:
        if self.nc is None or not self.nc.is_connected:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Successfully connected to NATS at {self.nats_url}")

    async def ensure_stream(self, stream_name: str, subjects: List[str])-> None:
        if not self.js:
            await self.connect()
        try:
            await self.js.add_stream(name = stream_name, subjects=subjects)
            logger.info(f"JetStream stream '{stream_name}' ensured for subjects {subjects}")
        except Exception as err:
            logger.debug(f"Stream '{stream_name}' notice/already exists: {err}")

    async def close(self) -> None:
        if self.nc and not self.nc.is_closed:
            await self.nc.drain()
            await self.nc.close()
            self.nc = None
            self.js = None
            logger.info("NATS connection drained and closed.")

