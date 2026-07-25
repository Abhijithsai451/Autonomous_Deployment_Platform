from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.nats.nats_client import EventBus
from packages.logging.structured_logs import StructuredLogger

log_manager = StructuredLogger(
    service_name="cortexops-organization",
    level= "INFO",
    initial_context = {"env": "production"}
)

logger = log_manager.get_logger()
async def example_workflow_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")


@asynccontextmanager
async def workflow_lifespan(app: FastAPI):
    # 1. Startup: Establish NATS connection for both Publisher & EventSubscriber
    await EventBus.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    # 2. Optional: Register any specific event listeners your service needs to audit/consume
    await EventBus.register_listener(
        stream="workflow_events",
        subject="workflow.Initialized",
        durable_name="workflow-service-user-invited-worker",
        handler=example_workflow_logging_handler
        )
    yield
    # 3. Shutdown: Disconnect cleanly from the NATS clusters
    await EventBus.shutdown()
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