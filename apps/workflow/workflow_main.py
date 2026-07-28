import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.workflow.api.v1 import blueprint_api, instance_api, task_api, timeline_api
from apps.workflow.infrastructure.outbox_publisher import OutboxPublisher
from apps.workflow.infrastructure.structured_logs import struct_logger as logger
from apps.workflow.infrastructure.workflow_nats_client import workflow_nats_client as nats


outbox_worker = OutboxPublisher(poll_interval_seconds=0.01)

async def example_workflow_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")


@asynccontextmanager
async def workflow_lifespan(app: FastAPI):
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    outbox_task = asyncio.create_task(outbox_worker.start())
    logger.info("Outbox Publisher Worker started successfully.")

    await nats.register_listener(
        subject="Initialized",
        durable_name="workflow-task-ready-worker",
        handler=example_workflow_logging_handler
        )
    yield

    outbox_worker.stop()
    await outbox_task

    await nats.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")

app = FastAPI(title="CortexOps Workflow Service", lifespan= workflow_lifespan)

@app.api_route("/health",methods=["GET", "HEAD"], tags=["System"])
async def health_check():
    """
    Service health check endpoint for monitoring, docker, and orchestration.
    """
    return {
        "status": "healthy",
        "service": "workflow-service"
    }

app.include_router(blueprint_api.router)

app.include_router(instance_api.router)

app.include_router(task_api.router)

app.include_router(timeline_api.router)
