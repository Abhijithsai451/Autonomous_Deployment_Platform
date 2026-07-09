from keycloak import KeycloakOpenID, KeycloakAdmin

from apps.identity.config.settings import settings


class KeycloakClient:
    def __init__(self):
        self.openid = KeycloakOpenID(
            server_url=settings.KEYCLOAK_URL,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            realm_name=settings.KEYCLOAK_REALM,
            client_secret_key=settings.KEYCLOAK_CLIENT_SECRET
        )
        self.admin = KeycloakAdmin(
            server_url=settings.KEYCLOAK_URL,
            username=settings.KEYCLOAK_ADMIN_USER,
            password=settings.KEYCLOAK_ADMIN_PASSWORD,
            realm_name=settings.KEYCLOAK_REALM,
            verify=True
        )

    def authenticate(self, username , password):
        return self.openid.token(username  = username, password = password)

    def refresh_token(self, refresh_token: str):
        return self.openid.refresh_token(refresh_token= refresh_token)

    def create_external_user(self, email: str, display_name: str) -> str:
        return self.admin.create_user({
            "email" : email,
            "username": email,
            "enabled": True,
            "first_name": display_name,
        }, exist_ok = False)
    

