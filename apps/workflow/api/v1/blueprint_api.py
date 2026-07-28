from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.workflow.application.blueprint_service import BlueprintService
from apps.workflow.infrastructure.database import workflow_db_session

router = APIRouter(prefix="/blueprints", tags=["Workflow Blueprints"])


class CreateBlueprintSchema(BaseModel):
    name: str
    definition: dict
    description: Optional[str] = None
    version: int = 1


@router.post("")
def create_blueprint(payload: CreateBlueprintSchema, db: Session = Depends(workflow_db_session)):
    svc = BlueprintService(db)
    return svc.create_blueprint(
        name=payload.name,
        definition=payload.definition,
        description=payload.description,
        version=payload.version
    )


@router.get("")
def list_blueprints(limit: int = 100, offset: int = 0, db: Session = Depends(workflow_db_session)):
    svc = BlueprintService(db)
    return  svc.get_blueprints(limit=limit, offset=offset)


@router.get("/{id}")
def get_blueprint(id: UUID, db: Session = Depends(workflow_db_session)):
    svc = BlueprintService(db)
    return  svc.get_blueprint_by_id(id)


@router.patch("/{id}")
def patch_blueprint(id: UUID, payload: dict, db: Session = Depends(workflow_db_session)):
    svc = BlueprintService(db)
    return  svc.update_blueprint(id, payload)