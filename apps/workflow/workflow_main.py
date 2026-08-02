import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from apps.workflow.api.v1 import blueprint_api, instance_api, task_api, timeline_api
from apps.workflow.application.idempotency_service import idempotent_listener
from apps.workflow.infrastructure.outbox_publisher import workflow_outbox_publisher
from apps.workflow.infrastructure.structured_logs import struct_logger as logger
from apps.workflow.infrastructure.workflow_nats_client import workflow_nats_client as nats


async def example_workflow_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")


@asynccontextmanager
async def workflow_lifespan(app: FastAPI):
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    outbox_task = asyncio.create_task(workflow_outbox_publisher.start())
    logger.info("Outbox Publisher Worker started successfully.")
    durable_name = "workflow-task-ready-worker"
    await nats.register_listener(
        subject="Initialized",
        durable_name=durable_name,
        handler=idempotent_listener(consumer_group=durable_name)(example_workflow_logging_handler))
    yield

    workflow_outbox_publisher.stop()
    await outbox_task

    await nats.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")

app = FastAPI(title="CortexOps Workflow Service", lifespan= workflow_lifespan)

@app.exception_handler(StaleDataError)
async def stale_data_exception_handler(request: Request, exc: StaleDataError):
    """
    Catches concurrent Mutation race conditions (SQL Alchemy Conflicts)
    Turns DB Errors into a clean HTTP 409 Conflict response.
    """
    logger.warning(f"Optimistic lock conflict detected: {exc}")
    return JSONResponse(
        status_code = 409,
        content = {
            "error" : "RESOURCE_CONFLICT",
            "message": "The resource was updated by another request. Please retry your operation."
        }
    )

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
