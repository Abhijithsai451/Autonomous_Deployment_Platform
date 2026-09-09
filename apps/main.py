from contextlib import asynccontextmanager

from dishka import make_async_container, FromDishka
from dishka.integrations.fastapi import FastapiProvider, setup_dishka, inject
from fastapi import FastAPI, APIRouter

from apps.core.providers import InfrastructureProvider, AppConfig, DatabaseSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.dishka_container.close()

def create_app():
    app = FastAPI(title= "ADD Platform API Platform", lifespan = lifespan)

    container = make_async_container(
        InfrastructureProvider(),
        FastapiProvider()
    )

    setup_dishka(container, app)

    app.include_router(api_router)
    return app

api_router = APIRouter(prefix= "/api/v1")

@api_router.get("/health")
@inject
async def health_check(
    config: FromDishka[AppConfig],
    session: FromDishka[DatabaseSession]
    )-> dict:

    return {
        "status": "healthy",
        "database_configured": config.db_url is not None
    }
