import hashlib
import secrets
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from apps.identity.domain.api_key import ApiKey
from apps.identity.domain.events.api_events import APIKeyCreatedEvent, APIKeyRevokedEvent
from apps.identity.domain.events.role_events import RoleCreatedEvent, RoleAssignedToUserEvent, RoleRemovedFromUserEvent
from apps.identity.domain.events.service_account_events import ServiceAccountCreatedEvent
from apps.identity.domain.outbox import OutboxEvent, OutboxStatus
from apps.identity.domain.events.user_events import *
from apps.identity.domain.role import *
from apps.identity.domain.service_account import ServiceAccount
from apps.identity.domain.user import UserStatus, User
from apps.identity.infrastructure.identity_nats_client import identity_nats_client as nats
from apps.identity.infrastructure.keycloak_client import KeycloakClient


class IdentityService:
    def __init__(self, db: Session, keycloak: KeycloakClient):
        self.db = db
        self.keycloak = keycloak
    def _log_event(self, aggregate_id: UUID, aggregate_type: str,  event_type: str, payload:dict):
        outbox_entry = OutboxEvent(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                event_type = event_type,
                payload= payload,
            status = OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)

    # --- Users ---
    async def invite_user(self, email: str, display_name: str) -> User:
        k_id = self.keycloak.create_external_user(email, display_name)
        user = User(keycloak_user_id=k_id, email=email, display_name=display_name,
                    status=UserStatus.INVITED)
        self.db.add(user)
        self.db.flush()
        user_created_event = UserInvitedEvent(id = user.id, keycloak_user_id= user.keycloak_user_id).subject
        user_payload = {
            "id": str(user.id),
            "keycloak_user_id": str(k_id),
            "email":user.email,
            "display_name": user.display_name,
            "status": user.status.value,
        }
        self._log_event(aggregate_id=user.id,aggregate_type="USER",
                        event_type=user_created_event,payload=user_payload)

        self.db.commit()
        self.db.refresh(user)
        return user

    async def update_user_status(self, user_id: UUID, status: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()

        if user:
            user.status = UserStatus(status)
            if user.status == UserStatus.ACTIVE:
                self.keycloak.enable_external_user(str(user.keycloak_user_id))
                user_activated_event = UserActivatedEvent(id=user.id, keycloak_user_id=user.keycloak_user_id).subject
                payload ={
                    "id": str(user.id),
                    "keycloak_user_id": str(user.keycloak_user_id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "status": user.status.value,
                }
                self._log_event(aggregate_id=user_id, aggregate_type="USER",
                                event_type=user_activated_event, payload=payload)
            elif user.status == UserStatus.DISABLED:
                self.keycloak.disable_external_user(str(user.keycloak_user_id))
                user_disabled_event = UserDisabledEvent(id=user.id, keycloak_user_id=user.keycloak_user_id).subject
                payload = {
                    "id": str(user.id),
                    "keycloak_user_id": str(user.keycloak_user_id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "status": user.status.value,
                }
                self._log_event(aggregate_id=user_id, aggregate_type="USER",
                                event_type=user_disabled_event, payload=payload)
            self.db.commit()
        return user

    async def delete_user(self, user_id: UUID):
        user = self.db.query(User).filter(User.id == user_id).first()
        user.status = UserStatus.DISABLED
        self.keycloak.disable_external_user(str(user.keycloak_user_id))
        user_disabled_event = UserDisabledEvent(id=user.id, keycloak_user_id=user.keycloak_user_id).subject
        payload = {
            "id": str(user.id),
            "keycloak_user_id": str(user.keycloak_user_id),
            "email": user.email,
            "display_name": user.display_name,
            "status": user.status.value,
        }
        self._log_event(aggregate_id=user_id, aggregate_type="USER",
                        event_type=user_disabled_event, payload=payload)
        self.db.commit()

    # --- Roles ---
    async def create_role(self, name: str, description: str) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        role_created_event = RoleCreatedEvent(id=role.id,).subject
        role_payload = {
            "id": str(role.id),
            "name": role.name,
            "description": role.description,
            "system_role":role.system_role,
        }
        self._log_event(aggregate_id=role.id, aggregate_type="ROLE",
                        event_type=role_created_event, payload=role_payload)

        self.db.commit()
        self.db.refresh(role)
        await nats.publish("RoleCreated", {"id": str(role.id), "name": role.name})
        return role

    async def assign_role(self, user_id: UUID, role_id: UUID):
        user = self.db.query(User).filter(User.id == user_id).first()
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if user and role:
            user.roles.append(role)
            role_assigned_event = RoleAssignedToUserEvent(id=role.id,user_id =user.id ).subject
            payload = {
                "id": str(role.id),
                "user_id": str(user.id)
            }
            self._log_event(aggregate_id=role.id, aggregate_type="USER_ROLES",
                            event_type=role_assigned_event, payload=payload)
            self.db.commit()
            self.db.refresh(role)
            self.db.refresh(user)


    async def remove_role(self, user_id: UUID, role_id: UUID):
        user = self.db.query(User).filter(User.id == user_id).first()
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if user and role in user.roles:
            user.roles.remove(role)
            role_removed_event = RoleRemovedFromUserEvent(id=role.id, user_id=user.id).subject
            payload = {
                "id": str(role.id),
                "user_id": str(user.id)
            }
            self._log_event(aggregate_id=role.id, aggregate_type="USER_ROLES",
                            event_type=role_removed_event, payload=payload)
            self.db.commit()


    # --- Service Accounts ---
    async def create_service_account(self, client_id: str, description: str) -> ServiceAccount:
        sa = ServiceAccount(client_id=client_id, description=description)
        self.db.add(sa)
        self.db.flush()
        sa_created_event = ServiceAccountCreatedEvent(id=sa.id, client_id = client_id).subject
        payload= {
            "id": str(sa.id),
            "client_id": str(client_id),
            "description": sa.description,
            "created_id": str(sa.created_at)
        }
        self._log_event(aggregate_id=sa.id,aggregate_type="ServiceAccount",event_type=sa_created_event, payload = payload)
        self.db.commit()
        self.db.refresh(sa)

        return sa

    # --- API Keys ---
    async def create_api_key(self, name: str, sa_id: UUID = None) -> tuple[ApiKey, str]:
        raw_key = f"cxop_{secrets.token_urlsafe(32)}"
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        key = ApiKey(name=name, service_account_id=sa_id, hashed_key=hashed)
        key_created_event = APIKeyCreatedEvent(id = key.id)
        payload = {
            "id": str(key.id),
            "service_account_id":str(sa_id),
            "name":key.name,
            "created_at": key.created_at
        }
        self._log_event(aggregate_id=key.id,aggregate_type="ApiKey",event_type=key_created_event, payload = payload)
        self.db.add(key)
        self.db.commit()
        return key, raw_key

    async def revoke_api_key(self, key_id: UUID):
        key = self.db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key:
            key.revoked_at = datetime.utcnow()
            key_revoked_event = APIKeyRevokedEvent(id=key.id)
            payload = {
                "id": str(key.id),
                "service_account_id": str(key.service_account_id),
                "name": key.name,
                "revoked_at": key.revoked_at
            }
            self._log_event(aggregate_id=key.id, aggregate_type="ApiKey", event_type=key_revoked_event,payload = payload)
            self.db.commit()