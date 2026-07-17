import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apps.identity.api.v1 import auth, organizations, users, roles_permissions, service_accounts, api_keys
from infrastructure.nats.nats_client import EventBus

logger = logging.getLogger("identity.main")

# Example background handler for testing/listening to events if needed
async def example_identity_logging_handler(payload: dict, metadata: dict):
    logger.info(f"Received event tracking hook: {metadata.get('event_type')} - ID: {payload.get('id')}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Establish NATS connection for both Publisher & EventSubscriber
    await EventBus.initialize()
    logger.info("NATS Messaging Core successfully initialized.")

    # 2. Optional: Register any specific event listeners your service needs to audit/consume
    # For example, if this service needs to listen to its own 'UserInvited' events:
    await EventBus.register_listener(
         stream="identity_events",
         subject="identity.userinvited",
         durable_name="identity-service-user-invited-worker",
         handler=example_identity_logging_handler
     )

    yield

    # 3. Shutdown: Disconnect cleanly from the NATS clusters
    await EventBus.shutdown()
    logger.info("NATS Messaging Core successfully disconnected.")

# Instantiate App Component
app = FastAPI(title="CortexOps Identity Service", lifespan=lifespan)

@app.api_route("/health",methods=["GET", "HEAD"], tags=["System"])
async def health_check():
    """
    Service health check endpoint for monitoring, docker, and orchestration.
    """
    return {
        "status": "healthy",
        "service": "identity-service"
    }

app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(roles_permissions.router)
app.include_router(service_accounts.router)
app.include_router(api_keys.router)