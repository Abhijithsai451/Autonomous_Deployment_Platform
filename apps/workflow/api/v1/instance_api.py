from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.workflow.application.instance_service import InstanceService
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


@router.post("")
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


@router.post("/{id}/pause")
async def pause_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.pause_instance(id)


@router.post("/{id}/resume")
async def resume_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.resume_instance(id)


@router.post("/{id}/cancel")
async def cancel_instance(id: UUID, payload: CancelInstanceSchema = None, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    reason = payload.reason if payload else None
    return await svc.cancel_instance(id, reason=reason)


@router.post("/{id}/retry")
async def retry_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.retry_instance(id)


@router.post("/{id}/signal")
async def signal_instance(id: UUID, payload: SignalInstanceSchema, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return await svc.signal_instance(id, signal_name=payload.signal_name, payload=payload.payload)