from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.identity.application.identity_service import IdentityService
from apps.identity.domain.organization import Organization
from apps.identity.infrastructure.database import get_db_session
from apps.identity.infrastructure.keycloak_client import KeycloakClient

router = APIRouter(prefix= "/organizations", tags=["Organizations"])

class CreateOrgSchema(BaseModel):
    name: str
    slug: str
    plan: str = "FREE"

@router.post("/")
async def create_org(payload: CreateOrgSchema, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    return await svc.create_organization(payload.name, payload.slug, payload.plan)

@router.get("/{id}")
def get_org(id: UUID, db: Session = Depends(get_db_session)):
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org: raise HTTPException(status_code=404, detail = "Organization Not Found")
    return org

@router.patch("/{id}")
async def patch_org(id: UUID, payload: dict, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    return await svc.update_organization(id, payload)
