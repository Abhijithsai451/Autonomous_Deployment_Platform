import asyncio
from apps.identity.infrastructure.identity_nats_client import identity_nats_client as nats
from apps.identity.infrastructure.outbox_publisher import IdentityOutboxPublisher
from apps.identity.infrastructure.structured_logs import struct_logger as logger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apps.identity.api.v1 import auth, users, roles_permissions, service_accounts, api_keys

identity_publisher = IdentityOutboxPublisher(poll_interval_seconds=0.01, batch_size=50)

@asynccontextmanager
async def identity_lifespan(app: FastAPI):
    await nats.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    task_publisher = asyncio.create_task(identity_publisher.start())
    yield
    logger.info("Shutting Down Identity Service")
    identity_publisher.stop()
    await task_publisher
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