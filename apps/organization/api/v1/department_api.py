from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.organization.application.department_service import DepartmentService
from apps.organization.domain.department import Department
from apps.organization.infrastructure.database import org_db_session
from packages.auth import auth_jwt

router = APIRouter(prefix="/departments", tags=["Departments"], dependencies=[Depends(auth_jwt)])

class CreateDepartmentSchema(BaseModel):
    organization_id: UUID
    name: str
    description: str
    type: str

class StatusUpdateSchema(BaseModel):
    status: str

@router.post("")
async def create_department(payload: CreateDepartmentSchema, db: Session = Depends(org_db_session)):
    svc = DepartmentService(db)
    return await svc.create_department(
        org_id=payload.organization_id,
        name=payload.name,
        description=payload.description,
        type=payload.type
    )

@router.get("")
def list_departments(db: Session = Depends(org_db_session)):
    return db.query(Department).all()

@router.get("/{id}")
def get_department(id: UUID, db: Session = Depends(org_db_session)):
    dept = db.query(Department).filter(Department.id == id).first()
    if not dept: raise HTTPException(status_code=404, detail="Department not found")
    return dept

@router.patch("/{id}")
async def patch_department(id: UUID, payload: dict, db: Session = Depends(org_db_session)):
    svc = DepartmentService(db)
    return await svc.update_department_data(id, payload)

@router.patch("/{id}/status")
async def change_status(id: UUID, payload: StatusUpdateSchema, db: Session = Depends(org_db_session)):
    svc = DepartmentService(db)
    return await svc.update_department_status(id, payload.status)