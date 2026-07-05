from contextlib import asynccontextmanager

from dishka import make_async_container, FromDishka
from dishka.integrations.fastapi import FastapiProvider, setup_dishka, inject
from fastapi import FastAPI, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.providers import InfrastructureProvider
from app.events.broker import EventBroker
from app.modules.platform.repositories import WorkflowRepository


@asynccontextmanager
async def lifespan(app: FastAPI):

    container = app.state.dishka_container
    await container.get(EventBroker)
    yield
    await app.state.dishka_container.close()

def create_app()-> FastAPI:
    app = FastAPI(title= "CortexOps Platform Backbone", lifespan = lifespan)
    container = make_async_container(InfrastructureProvider(), FastapiProvider())
    setup_dishka(container, app)
    return app

api_router = APIRouter(prefix = "/api/v1")

@api_router.post("/workflows")
@inject
async def trigger_workflow(
        payload: dict,
        repo: FromDishka[WorkflowRepository],
        broker: FromDishka[EventBroker],
        session: FromDishka[AsyncSession]
            )-> dict:
    wf = await repo.create(
        description = payload.get("description","Agentic Devops Job"),
        context_payload = payload.get("context",{})
    )

    event_payload = {
        "workflow_id": str(wf.id),
        "status": wf.status,
        "payload": wf.context_payload
    }
    await broker.publish("cortexops.workflow.started", event_payload)

    await session.commit()
    return {"workflow_id": str(wf.id), "status": "initialized"}

