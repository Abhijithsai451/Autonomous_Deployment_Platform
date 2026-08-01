import os

from apps.identity.infrastructure.identity_nats_client import identity_nats_client as nats
from apps.identity.infrastructure.structured_logs import struct_logger as logger
from packages.logging.structured_logs import StructuredLogger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apps.identity.api.v1 import auth, organizations, users, roles_permissions, service_accounts, api_keys

log_manager = StructuredLogger(
    service_name="cortexops-identity",
    level= "INFO",
    initial_context = {"env": "production"}
)

async def identity_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")

@asynccontextmanager
async def identity_lifespan(app: FastAPI):
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")
    TESTING = os.getenv("TESTING", "false").lower() == "true"
    durable_suffix = "-test" if TESTING else ""
    await nats.register_listener(
         subject="UserCreated",
         durable_name=f"identity-user-created-worker{durable_suffix}",
         handler=identity_logging_handler
     )

    yield

    await nats.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")

app = FastAPI(title="CortexOps Identity Service", lifespan=identity_lifespan)

@app.api_route("/health",methods=["GET", "HEAD"], tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "identity-service"
    }

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles_permissions.router)
app.include_router(service_accounts.router)
app.include_router(api_keys.router)