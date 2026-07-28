from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from apps.workflow.application.instance_service import InstanceService
from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.infrastructure.database import workflow_db_session

router = APIRouter(prefix="/instances", tags=["Workflow Instances"])


class CreateInstanceSchema(BaseModel):
    blueprint_id: UUID
    input_data: dict = {}
    started_by: Optional[UUID] = None


class SignalInstanceSchema(BaseModel):
    signal_name: str
    payload: dict = {}


class CancelInstanceSchema(BaseModel):
    reason: Optional[str] = None

class TimeoutInstanceSchema(BaseModel):
    reason: Optional[str] = "Execution timeout reached"
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_instance(payload: CreateInstanceSchema, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.create_instance(
        blueprint_id=payload.blueprint_id,
        input_data=payload.input_data,
        started_by=payload.started_by
    )


@router.get("")
async def list_instances(limit: int = 100, offset: int = 0, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.get_instances(limit=limit, offset=offset)


@router.get("/{id}")
async def get_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.get_instance_by_id(id)


@router.post("/{id}/start")
async def start_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return await svc.start_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/pause")
async def pause_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return await svc.pause_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/resume")
async def resume_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return await svc.resume_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/cancel")
async def cancel_instance(id: UUID, payload: Optional[CancelInstanceSchema] = None, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    reason = payload.reason if payload and payload.reason else "User cancelled execution"
    try:
        return await svc.cancel_instance(id, reason=reason)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/retry")
async def retry_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return await svc.retry_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/signal")
async def signal_instance(id: UUID, payload: SignalInstanceSchema, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.signal_instance(id, signal_name=payload.signal_name, payload=payload.payload)


@router.post("/{id}/complete")
async def complete_instance(id: UUID, payload: dict = {}, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return await svc.complete_instance(id, output_data=payload)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/timeout")
async def timeout_instance(id: UUID, payload: Optional[TimeoutInstanceSchema] = None, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    reason = payload.reason if payload and payload.reason else "Execution timeout reached"
    try:
        return await svc.timeout_instance(id, reason=reason)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))