from sqlalchemy.orm import Session

from apps.identity.infrastructure.keycloak_client import KeycloakClient


class AuthService:
    def __init__(self, db: Session, keycloak: KeycloakClient):
        self.db = db
        self.keycloak = keycloak

    def handle_login(self, username, password):
        tokens = self.keycloak.authenticate_user(username, password)
        return tokens

    def handle_refresh(self, refresh_token: str):
        return self.keycloak.refresh_token(refresh_token)


