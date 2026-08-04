from uuid import UUID

from fastapi import Depends, HTTPException, APIRouter
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from apps.identity.application.identity_service import IdentityService
from apps.identity.domain.user import User
from apps.identity.infrastructure.database import get_db_session
from apps.identity.infrastructure.keycloak_client import KeycloakClient
from packages.auth.auth_jwt import get_current_user, CurrentUser

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(get_current_user)])

class InviteUserSchema(BaseModel):
    organization_id: UUID
    email: EmailStr
    display_name: str

class StatusUpdateSchema(BaseModel):
    status: str

async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "roles": current_user.realm_roles,
    }
@router.post("/invite")
async def invite(payload: InviteUserSchema, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    return await svc.invite_user(payload.organization_id, payload.email, payload.display_name)

@router.get("")
def list_users(db: Session = Depends(get_db_session)):
    return db.query(User).all()

@router.get("/{id}")
def get_user(id: UUID, db: Session = Depends(get_db_session)):
    user = db.query(User).filter(User.id == id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{id}")
def patch_user(id: UUID, payload: dict, db: Session = Depends(get_db_session)):
    user = db.query(User).filter(User.id == id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    for k, v in payload.items(): setattr(user, k, v)
    db.commit()
    return user

@router.patch("/{id}/status")
async def change_status(id: UUID, payload: StatusUpdateSchema, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    return await svc.update_user_status(id, payload.status)

@router.delete("/{id}")
async def delete_user(id: UUID, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    await svc.delete_user(id)
    return {"status": "deleted"}

@router.post("/{id}/roles")
async def assign_role(id: UUID, role_id: UUID, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    await svc.assign_role(id, role_id)
    return {"status": "assigned"}

@router.delete("/{id}/roles/{roleId}")
async def remove_role(id: UUID, roleId: UUID, db: Session = Depends(get_db_session)):
    svc = IdentityService(db, KeycloakClient())
    await svc.remove_role(id, roleId)
    return {"status": "removed"}