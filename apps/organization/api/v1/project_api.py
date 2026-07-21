from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.organization.application.project_service import ProjectService
from apps.organization.domain.project import Project
from apps.organization.infrastructure.database import org_db_session

router = APIRouter(prefix="/projects", tags=["Projects"])

class CreateProjectSchema(BaseModel):
    organization_id: UUID
    name: str
    description: str
    lifecycle: str = "ACTIVE"

class StatusUpdateSchema(BaseModel):
    status: str

@router.post("")
async def create_project(payload: CreateProjectSchema, db: Session = Depends(org_db_session)):
    svc = ProjectService(db)
    return await svc.create_projects(
        org_id=payload.organization_id,
        name=payload.name,
        description=payload.description,
        lifecycle=payload.lifecycle
    )

@router.get("")
def list_projects(db: Session = Depends(org_db_session)):
    return db.query(Project).all()

@router.get("/{id}")
def get_project(id: UUID, db: Session = Depends(org_db_session)):
    project = db.query(Project).filter(Project.id == id).first()
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{id}")
async def patch_project(id: UUID, payload: dict, db: Session = Depends(org_db_session)):
    svc = ProjectService(db)
    return await svc.update_project_data(id, payload)

@router.patch("/{id}/status")
async def change_status(id: UUID, payload: StatusUpdateSchema, db: Session = Depends(org_db_session)):
    svc = ProjectService(db)
    return await svc.update_project_status(id, payload.status)