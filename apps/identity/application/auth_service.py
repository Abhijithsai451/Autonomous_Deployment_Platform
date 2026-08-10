from uuid import UUID

from sqlalchemy.orm import Session

from apps.identity.domain.outbox import OutboxEvent, OutboxStatus
from apps.identity.infrastructure.keycloak_client import KeycloakClient

class AuthService:
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

    def handle_login(self, username, password):
        return self.keycloak.authenticate_user(username, password)

    def handle_logout(self, refresh_token: str):
        self.keycloak.logout_user(refresh_token)

    def handle_refresh(self, refresh_token: str):
        return self.keycloak.refresh_token(refresh_token)

    def get_current_user_info(self, token: str):
        return self.keycloak.userinfo(token)