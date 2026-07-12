from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await IdentityEventBus.initialize()
    yield
    await IdentityEventBus.shutdown()

app = FastAPI(title="CortexOps Identity Service", lifespan=lifespan)

# Setup Layer Endpoints
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(roles_permissions.router)
app.include_router(service_accounts.router)
app.include_router(api_keys.router)