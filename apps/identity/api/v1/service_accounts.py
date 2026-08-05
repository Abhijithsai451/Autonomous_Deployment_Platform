from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.identity.application.identity_service import IdentityService
from apps.identity.domain.service_account import ServiceAccount
from apps.identity.infrastructure.database import identity_db_session
from apps.identity.infrastructure.keycloak_client import KeycloakClient
from packages.auth.auth_jwt import get_current_user

router = APIRouter(prefix="/service-accounts", tags=["Service Accounts"], dependencies=[Depends(get_current_user)])

class CreateSASchema(BaseModel):
    organization_id: UUID
    client_id: str
    description: str

@router.post("")
async def create_sa(payload: CreateSASchema, db: Session = Depends(identity_db_session)):
    svc = IdentityService(db, KeycloakClient())
    return await svc.create_service_account(payload.organization_id, payload.client_id, payload.description)

@router.get("")
def list_sa(db: Session = Depends(identity_db_session)):
    return db.query(ServiceAccount).all()

@router.patch("/{id}")
def patch_sa(id: UUID, payload: dict, db: Session = Depends(identity_db_session)):
    sa = db.query(ServiceAccount).filter(ServiceAccount.id == id).first()
    if not sa: raise HTTPException(status_code=404, detail="Service Account not found")
    for k, v in payload.items(): setattr(sa, k, v)
    db.commit()
    return sa

@router.delete("/{id}")
def delete_sa(id: UUID, db: Session = Depends(identity_db_session)):
    sa = db.query(ServiceAccount).filter(ServiceAccount.id == id).first()
    if not sa: raise HTTPException(status_code=404, detail="Service Account not found")
    db.delete(sa)
    db.commit()
    return {"status": "deleted"}