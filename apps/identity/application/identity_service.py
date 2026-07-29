import hashlib
import secrets
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from apps.identity.domain.api_key import ApiKey
from apps.identity.domain.organization import Organization
from apps.identity.domain.role import Role
from apps.identity.domain.service_account import ServiceAccount
from apps.identity.domain.user import UserStatus, User
from apps.identity.infrastructure.identity_nats_client import identity_nats_client as nats
from apps.identity.infrastructure.keycloak_client import KeycloakClient


class IdentityService:
    def __init__(self, db: Session, keycloak: KeycloakClient):
        self.db = db
        self.keycloak = keycloak

    # --- Organizations ---
    async def create_organization(self, name: str, slug: str, plan: str) -> Organization:
        org = Organization(name=name, slug=slug, plan=plan)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        await nats.publish("OrganizationCreated", {"id": str(org.id), "slug": org.slug})
        return org

    async def update_organization(self, org_id: UUID, updates: dict) -> Organization:
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if org:
            for k, v in updates.items():
                setattr(org, k, v)
            self.db.commit()
            await nats.publish("OrganizationUpdated", {"id": str(org.id)})
        return org

    # --- Users ---
    async def invite_user(self, org_id: UUID, email: str, display_name: str) -> User:
        k_id = self.keycloak.create_external_user(email, display_name)
        user = User(organization_id=org_id, keycloak_user_id=k_id, email=email, display_name=display_name,
                    status=UserStatus.INVITED)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        await nats.publish("UserInvited", {"id": str(user.id), "email": user.email})
        return user

    async def update_user_status(self, user_id: UUID, status: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.status = UserStatus(status)
            if user.status == UserStatus.ACTIVE:
                self.keycloak.enable_external_user(str(user.keycloak_user_id))
                await nats.publish("UserActivated", {"id": str(user.id)})
            elif user.status == UserStatus.DISABLED:
                self.keycloak.disable_external_user(str(user.keycloak_user_id))
                await nats.publish("UserDisabled", {"id": str(user.id)})
            self.db.commit()
        return user

    async def delete_user(self, user_id: UUID):
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            self.keycloak.delete_external_user(str(user.keycloak_user_id))
            self.db.delete(user)
            self.db.commit()

    # --- Roles ---
    async def create_role(self, org_id: UUID, name: str, description: str) -> Role:
        role = Role(organization_id=org_id, name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        await nats.publish("RoleCreated", {"id": str(role.id), "name": role.name})
        return role

    async def assign_role(self, user_id: UUID, role_id: UUID):
        user = self.db.query(User).filter(User.id == user_id).first()
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if user and role:
            user.roles.append(role)
            self.db.commit()
            await nats.publish("RoleAssignedToUser",
                                                   {"user_id": str(user_id), "role_id": str(role_id)})

    async def remove_role(self, user_id: UUID, role_id: UUID):
        user = self.db.query(User).filter(User.id == user_id).first()
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if user and role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            await nats.publish("RoleRemovedFromUser",
                                                   {"user_id": str(user_id), "role_id": str(role_id)})

    # --- Service Accounts ---
    async def create_service_account(self, org_id: UUID, client_id: str, description: str) -> ServiceAccount:
        sa = ServiceAccount(organization_id=org_id, client_id=client_id, description=description)
        self.db.add(sa)
        self.db.commit()
        self.db.refresh(sa)
        await nats.publish("ServiceAccountCreated", {"id": str(sa.id), "client_id": sa.client_id})
        return sa

    # --- API Keys ---
    async def create_api_key(self, org_id: UUID, name: str, sa_id: UUID = None) -> tuple[ApiKey, str]:
        raw_key = f"cxop_{secrets.token_urlsafe(32)}"
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        key = ApiKey(organization_id=org_id, name=name, service_account_id=sa_id, hashed_key=hashed)
        self.db.add(key)
        self.db.commit()
        await nats.publish("ApiKeyCreated", {"id": str(key.id), "name": key.name})
        return key, raw_key

    async def revoke_api_key(self, key_id: UUID):
        key = self.db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.revoked_at = datetime.utcnow()
            self.db.commit()
            await nats.publish("ApiKeyRevoked", {"id": str(key_id)})