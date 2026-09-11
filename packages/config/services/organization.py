from pydantic_settings import BaseSettings, SettingsConfigDict


class OrganizationServiceSettings(BaseSettings):
    ORGANIZATION_DATABASE_URL: str
    NATS_URL: str

    model_config = SettingsConfigDict(extra="ignore")