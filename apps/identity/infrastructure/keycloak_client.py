from keycloak import KeycloakOpenID, KeycloakAdmin

from packages.config.settings import settings


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

    def authenticate_user(self, username , password):
        return self.openid.token(username  = username, password = password)
    def logout_user(self, refresh_token: str):
        self.openid.logout(refresh_token)

    def refresh_token(self, refresh_token: str):
        return self.openid.refresh_token(refresh_token= refresh_token)

    def userinfo(self, token: str):
        return self.openid.userinfo(token=token)

    def create_external_user(self, email: str, display_name: str) -> str:
        return self.admin.create_user({
            "email" : email,
            "username": email,
            "enabled": True,
            "first_name": display_name,
        }, exist_ok = False)

    def disable_external_user(self, keycloak_user_id: str):
        self.admin.update_user(user_id=keycloak_user_id, payload={"enabled": False})

    def enable_external_user(self, keycloak_user_id: str):
        self.admin.update_user(user_id=keycloak_user_id, payload={"enabled": True})

    def delete_external_user(self, keycloak_user_id: str):
        self.admin.delete_user(user_id=keycloak_user_id)


