from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.organization.api.v1 import organization_api, project_api, department_api
from apps.organization.infrastructure.database import org_db_client
from apps.organization.infrastructure.org_nats_client import org_nats_client as nats
from apps.organization.infrastructure.structured_logs import struct_logger as logger
from packages.logging.structured_logs import StructuredLogger

log_manager = StructuredLogger(
    service_name="cortexops-organization",
    level= "INFO",
    initial_context = {"env": "production"}
)

async def user_invited_event_handler(payload: dict, metadata: dict):
    user_id = payload.get("id")
    email = payload.get("email")
    logger.info(f" Organization received UserInvited event for User: {user_id} {email}")
    logger.info("Organization publishing DepartmentCreated Event ")
    await nats.publish(
        event_type="organization.events.department.created",
        payload = {
            "id": f"dept-for-{user_id}",
            "name": "Default Department",
            "organization_id": "org-001"
        }
    )

@asynccontextmanager
async def organization_lifespan(app: FastAPI):
    if not org_db_client.check_health():
        raise RuntimeError("Organization database health check failed on startup!")
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")
    await nats.client.ensure_stream(stream_name="identity_events", subjects=['identity.>'])
    await nats.register_listener(
        subject="identity.events.user.invited",
        durable_name="organization-service-user-invited-worker",
        handler=user_invited_event_handler,
        stream = "identity_events"
        )
    yield
    await nats.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")



app = FastAPI(title="ADD Platform Organization Service", lifespan=organization_lifespan)

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

