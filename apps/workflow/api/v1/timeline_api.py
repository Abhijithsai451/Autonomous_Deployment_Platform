from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.workflow.application.timeline_service import TimelineService
from apps.workflow.infrastructure.database import workflow_db_session
from packages.auth import auth_jwt

router = APIRouter(prefix="/instances", tags=["Timeline"], dependencies=[Depends(auth_jwt)])

@router.get("/{id}/timeline")
def get_instance_timeline(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = TimelineService(db)
    return svc.get_instance_timeline(id)