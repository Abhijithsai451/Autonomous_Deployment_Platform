from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.identity.application.identity_service import IdentityService
from apps.identity.domain.api_key import ApiKey
from apps.identity.infrastructure.database import identity_db_session
from apps.identity.infrastructure.keycloak_client import KeycloakClient

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

class CreateKeySchema(BaseModel):
    organization_id: UUID
    name: str
    service_account_id: UUID = None

@router.post("")
async def create_key(payload: CreateKeySchema, db: Session = Depends(identity_db_session)):
    svc = IdentityService(db, KeycloakClient())
    key_entity, raw_token = await svc.create_api_key(payload.organization_id, payload.name, payload.service_account_id)
    return {"id": key_entity.id, "name": key_entity.name, "token": raw_token}

@router.get("")
def list_keys(db: Session = Depends(identity_db_session)):
    return db.query(ApiKey).filter(ApiKey.revoked_at.is_(None)).all()

@router.delete("/{id}")
async def revoke_key(id: UUID, db: Session = Depends(identity_db_session)):
    svc = IdentityService(db, KeycloakClient())
    await svc.revoke_api_key(id)
    return {"status": "revoked"}