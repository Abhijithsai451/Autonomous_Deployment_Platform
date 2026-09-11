from packages.config.services.identity import IdentityServiceSettings

_settings = IdentityServiceSettings()
class IdentitySettingsAdapter():
    def __init__(self, config: IdentityServiceSettings) -> None:
        self._config = config

    @property
    def IDENTITY_DATABASE_URL(self) -> str:
        return self._config.IDENTITY_DATABASE_URL

    @property
    def KEYCLOAK_URL(self) -> str:
        return self._config.KEYCLOAK_URL

    @property
    def KEYCLOAK_REALM(self) -> str:
        return self._config.KEYCLOAK_REALM

    @property
    def KEYCLOAK_CLIENT_ID(self) -> str:
        return self._config.KEYCLOAK_CLIENT_ID

    @property
    def KEYCLOAK_CLIENT_SECRET(self) -> str:
        return self._config.KEYCLOAK_CLIENT_SECRET

    @property
    def KEYCLOAK_ADMIN_USER(self) -> str:
        return self._config.KEYCLOAK_ADMIN_USER

    @property
    def KEYCLOAK_ADMIN_PASSWORD(self) -> str:
        return self._config.KEYCLOAK_ADMIN_PASSWORD

    @property
    def NATS_URL(self) -> str:
        return self._config.NATS_URL

identity_settings = IdentitySettingsAdapter(_settings)
