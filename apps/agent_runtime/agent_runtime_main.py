import asyncio
from fastapi import FastAPI

from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client as nats
from apps.agent_runtime.infrastructure.outbox_publisher import AgentRuntimeOutboxPublisher
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger

agent_runtime_publisher = AgentRuntimeOutboxPublisher(poll_interval_seconds=0.01, batch_size=50)

async def agent_runtime_lifespan(app: FastAPI):
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    task_publisher = asyncio.create_task(agent_runtime_publisher.start())
    yield
    logger.info("Shutting Down Agent Runtime Service")
    agent_runtime_publisher.stop()
    await task_publisher
    await nats.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")

app = FastAPI(title="CortexOps Agent Runtime Service", lifespan=agent_runtime_lifespan)


@app.api_route("/health",methods=["GET", "HEAD"], tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "agent_runtime-service"
    }