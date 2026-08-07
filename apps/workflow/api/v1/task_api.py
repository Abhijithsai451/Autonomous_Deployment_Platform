from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.workflow.application.task_service import TaskService
from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.infrastructure.database import workflow_db_session
from packages.auth.auth_jwt import get_current_user

router = APIRouter(tags=["Tasks"], dependencies=[Depends(get_current_user)])

class StartTaskSchema(BaseModel):
    assigned_agent_id: Optional[UUID] = None


class FailTaskSchema(BaseModel):
    error_details: dict = {}


class ApprovalRequestSchema(BaseModel):
    approvers: list = []
    details: dict = {}


class ApprovalReceiveSchema(BaseModel):
    approved_by: str
    metadata: dict = {}

@router.get("/tasks/{id}")
def get_task(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return svc.get_task_by_id(id)


@router.get("/instances/{id}/tasks")
def get_instance_tasks(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    return  svc.get_tasks_by_instance(id)


@router.post("/tasks/{id}/start")
def start_task(id: UUID, payload: Optional[StartTaskSchema] = None, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    assigned_agent_id = payload.assigned_agent_id if payload else None
    try:
        return svc.start_task(id, assigned_agent_id=assigned_agent_id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/tasks/{id}/complete")
def complete_task(id: UUID, payload: dict = {}, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    try:
        return svc.complete_task(id, output_data=payload)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/tasks/{id}/fail")
def fail_task(id: UUID, payload: Optional[FailTaskSchema] = None, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    error_details = payload.error_details if payload else {}
    try:
        return svc.fail_task(id, error_details=error_details)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/tasks/{id}/retry")
def retry_task(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    try:
        return svc.retry_task(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/tasks/{id}/cancel")
def cancel_task(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    try:
        return  svc.cancel_task(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/tasks/{id}/request-approval")
def request_approval(id: UUID, payload: ApprovalRequestSchema, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    try:
        return svc.request_approval(id, required_approvers=payload.approvers, details=payload.details)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/tasks/{id}/receive-approval")
def receive_approval(id: UUID, payload: ApprovalReceiveSchema, db: Session = Depends(workflow_db_session)):
    svc = TaskService(db)
    try:
        return svc.receive_approval(id, approved_by=payload.approved_by, approval_metadata=payload.metadata)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))