import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from apps.agent_runtime.api import health
from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client as nats
from apps.agent_runtime.infrastructure.outbox_publisher import agent_outbox_publisher
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger

@asynccontextmanager
async def agent_lifespan(app: FastAPI):
    logger.info("Initializing the Agent Runtime Daemon ....")
    await nats.initialize()
    logger.info("NATS Core Messaging is successfully initialized for Agent Runtime Service")
    outbox_task = asyncio.create_task(agent_outbox_publisher.start())
    logger.info("Agent Runtime Outbox Publisher Worker started successfully.")

    yield

    agent_outbox_publisher.stop()
    await outbox_task

    await nats.shutdown()
    logger.info("NATS Messaging Core successfully disconnected from Agent Runtime.")
app = FastAPI(title="ADD Platform Agent Runtime Service", lifespan= agent_lifespan)

@app.exception_handler(StaleDataError)
async def stale_data_exception_handler(request: Request, exc: StaleDataError):
    logger.warning(f"Optimistic lock conflict detected in Agent Runtime: {exc}")
    return JSONResponse(
        status_code=409,
        content={
            "error": "RESOURCE_CONFLICT",
            "message": "The agent runtime resource was updated by another request. Please retry."
        }
    )


app.include_router(health.router)