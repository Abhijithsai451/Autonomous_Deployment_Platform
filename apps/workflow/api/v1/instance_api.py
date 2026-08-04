from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from apps.workflow.application.instance_service import InstanceService
from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.infrastructure.database import workflow_db_session
from packages.auth.auth_jwt import get_current_user

router = APIRouter(prefix="/instances", tags=["Workflow Instances"], dependencies=[Depends(get_current_user)])

class PaginatedInstanceResponse(BaseModel):
    items : List[dict]
    total : int
    limit : int
    offset : int
    has_more : bool

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
def create_instance(payload: CreateInstanceSchema, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return svc.create_instance(
        blueprint_id=payload.blueprint_id,
        input_data=payload.input_data,
        started_by=payload.started_by
    )

@router.get("", response_model = PaginatedInstanceResponse)
def list_instances(
        limit: int = Query(20, description = "Items per page"),
        offset: int = Query(0, descripiton = "Items to skip"),
        instance_status: Optional[str]= Query(None, description="Filter by instance status"),
        blueprint_id: Optional[UUID] = Query(None, description="Filter by blueprint ID"),
        db: Session = Depends(workflow_db_session)):
    limit = min(max(1, limit),100)
    offset = max(0, offset)
    svc = InstanceService(db)
    return svc.get_instances(limit=limit, offset=offset, status_filter = instance_status, blueprint_id=blueprint_id)


@router.get("/{id}")
def get_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return svc.get_instance_by_id(id)


@router.post("/{id}/start")
def start_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return  svc.start_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/pause")
def pause_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return  svc.pause_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/resume")
def resume_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return  svc.resume_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/cancel")
def cancel_instance(id: UUID, payload: Optional[CancelInstanceSchema] = None, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    reason = payload.reason if payload and payload.reason else "User cancelled execution"
    try:
        return  svc.cancel_instance(id, reason=reason)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/retry")
def retry_instance(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return  svc.retry_instance(id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/signal")
def signal_instance(id: UUID, payload: SignalInstanceSchema, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    return  svc.signal_instance(id, signal_name=payload.signal_name, payload=payload.payload)


@router.post("/{id}/complete")
def complete_instance(id: UUID, payload: dict = {}, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    try:
        return  svc.complete_instance(id, output_data=payload)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{id}/timeout")
def timeout_instance(id: UUID, payload: Optional[TimeoutInstanceSchema] = None, db: Session = Depends(workflow_db_session)):
    svc = InstanceService(db)
    reason = payload.reason if payload and payload.reason else "Execution timeout reached"
    try:
        return  svc.timeout_instance(id, reason=reason)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))