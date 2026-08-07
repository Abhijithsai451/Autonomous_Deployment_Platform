from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.identity.application.identity_service import IdentityService
from apps.identity.domain.permission import Permission
from apps.identity.domain.role import Role
from apps.identity.infrastructure.database import identity_db_session
from apps.identity.infrastructure.keycloak_client import KeycloakClient
from packages.auth.auth_jwt import get_current_user

router = APIRouter(tags= ["Roles & Permissions"]) #, dependencies=[Depends(get_current_user)])

class CreateRoleSchema(BaseModel):
    organization_id: UUID
    name: str
    description: str

@router.post("/roles")
async def create_role(payload: CreateRoleSchema, db: Session = Depends(identity_db_session)):
    svc = IdentityService(db, KeycloakClient())
    return await svc.create_role(payload.organization_id, payload.name, payload.description)

@router.get("/roles")
def get_roles(db: Session = Depends(identity_db_session)):
    return db.query(Role).all()

@router.patch("/roles/{id}")
def patch_role(id: UUID, payload: dict, db: Session = Depends(identity_db_session)):
    role = db.query(Role).filter(Role.id == id).first()
    if not role: raise HTTPException(status_code=404, detail="Role not found")
    for k, v in payload.items(): setattr(role, k, v)
    db.commit()
    return role

@router.delete("/roles/{id}")
def delete_role(id: UUID, db: Session = Depends(identity_db_session)):
    role = db.query(Role).filter(Role.id == id).first()
    if not role: raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"status": "deleted"}

@router.get("/permissions")
def get_permissions(db: Session = Depends(identity_db_session)):
    return db.query(Permission).all()