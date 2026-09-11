from packages.config.services.organization import OrganizationServiceSettings

_settings = OrganizationServiceSettings()

class OrganizationSettingsAdapter():
    def __init__(self, config: OrganizationServiceSettings) -> None:
        self._config = config

    @property
    def ORGANIZATION_DATABASE_URL(self) -> str:
        return self._config.ORGANIZATION_DATABASE_URL

    @property
    def NATS_URL(self) -> str:
        return self._config.NATS_URL

org_settings = OrganizationSettingsAdapter(_settings)