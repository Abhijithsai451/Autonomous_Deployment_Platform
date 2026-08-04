from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID
from apps.organization.application.org_service import OrganizationService
from apps.organization.domain.organization import Organization
from apps.organization.infrastructure.database import org_db_session
from packages.auth import auth_jwt

router = APIRouter(prefix="/organizations",tags=["Organizations"], dependencies=[Depends(auth_jwt)])

class CreateOrgSchema(BaseModel):
    name: str
    slug: str
    status: str = "ACTIVE"

class StatusUpdateSchema(BaseModel):
    status: str
@router.post("")
async def create_org(payload: CreateOrgSchema, db: Session = Depends(org_db_session)):
    svc = OrganizationService(db)
    return await svc.create_organization(payload.name, payload.slug)

@router.get("")
def list_organizations(db: Session = Depends(org_db_session)):
    return db.query(Organization).all()


@router.get("/{id}")
def get_organization(id: UUID, db: Session = Depends(org_db_session)):
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org: raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.patch("/{id}")
async def patch_organization(id: UUID, payload: dict, db: Session = Depends(org_db_session)):
    svc = OrganizationService(db)
    return await svc.update_organization(id, payload)

@router.patch("/{id}/status")
async def change_status(id: UUID, payload: StatusUpdateSchema, db: Session = Depends(org_db_session)):
    svc = OrganizationService(db)
    return await svc.update_organization_status(id, payload.status)

@router.post("/{id}/suspend")
async def suspend(id: UUID, db: Session = Depends(org_db_session)):
    svc = OrganizationService(db)
    await svc.suspend_organization(id)
    return {"status": "suspended"}
