from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.organization.api.v1 import organization_api, project_api, department_api
from apps.organization.infrastructure.org_nats_client import org_nats_client as nats
from apps.organization.infrastructure.structured_logs import struct_logger as logger
from packages.logging.structured_logs import StructuredLogger

log_manager = StructuredLogger(
    service_name="cortexops-organization",
    level= "INFO",
    initial_context = {"env": "production"}
)

async def example_organization_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")

@asynccontextmanager
async def organization_lifespan(app: FastAPI):
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    await nats.register_listener(
        subject="UserInvited",
        durable_name="organization-service-user-invited-worker",
        handler=example_organization_logging_handler
        )
    yield
    await nats.shutdown()
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

