from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.workflow.application.task_service import TaskService
from apps.workflow.infrastructure.database import workflow_db_session

router = APIRouter(tags=["Tasks"])

class ApprovalRequestSchema(BaseModel):
    approvers: list = []
    details: dict = {}

class ApprovalReceiveSchema(BaseModel):
    approved_by: str
    metadata: dict = {}

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

@router.post("/tasks/{id}/complete")
async def complete_task(id: UUID, payload: dict = {}, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.complete_task(id, output_data=payload)

@router.post("/tasks/{id}/request-approval")
async def request_approval(id: UUID, payload: ApprovalRequestSchema, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.request_approval(id, required_approvers=payload.approvers, details=payload.details)

@router.post("/tasks/{id}/receive-approval")
async def receive_approval(id: UUID, payload: ApprovalReceiveSchema, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return await svc.receive_approval(id, approved_by=payload.approved_by, approval_metadata=payload.metadata)