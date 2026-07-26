from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.workflow.application.task_service import TaskService
from apps.workflow.infrastructure.database import workflow_db_session

router = APIRouter(tags=["Tasks"])


@router.get("/tasks/{id}")
async def get_task(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.get_task_by_id(id)


@router.get("/instances/{id}/tasks")
async def get_instance_tasks(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.get_tasks_by_instance(id)


@router.post("/tasks/{id}/retry")
async def retry_task(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.retry_task(id)


@router.post("/tasks/{id}/cancel")
async def cancel_task(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.cancel_task(id)