from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.organization.api.v1 import organization_api, project_api, department_api
from infrastructure.nats.nats_client import EventBus
from packages.logging.structured_logs import StructuredLogger

log_manager = StructuredLogger(
    service_name="cortexops-organization",
    level= "INFO",
    initial_context = {"env": "production"}
)

logger = log_manager.get_logger()
async def example_organization_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")

@asynccontextmanager
async def organization_lifespan(app: FastAPI):
    # 1. Startup: Establish NATS connection for both Publisher & EventSubscriber
    await EventBus.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    # 2. Optional: Register any specific event listeners your service needs to audit/consume
    await EventBus.register_listener(
        stream="identity_events",
        subject="identity.userinvited",
        durable_name="identity-service-user-invited-worker",
        handler=example_organization_logging_handler
        )
    yield
    # 3. Shutdown: Disconnect cleanly from the NATS clusters
    await EventBus.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")



app = FastAPI(title="CortexOps Organization Service", lifespan=organization_lifespan)

@app.api_route("/health",methods=["GET", "HEAD"], tags=["System"])
async def health_check():
    """
    Service health check endpoint for monitoring, docker, and orchestration.
    """
    return {
        "status": "healthy",
        "service": "organization-service"
    }
app.include_router(organization_api.router)

app.include_router(project_api.router)

app.include_router(department_api.router)

