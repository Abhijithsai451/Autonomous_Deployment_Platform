from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentityServiceSettings(BaseSettings):
    IDENTITY_DATABASE_URL: str = Field(...)
    KEYCLOAK_URL: str = Field(...)
    KEYCLOAK_REALM: str = Field(...)
    KEYCLOAK_CLIENT_ID: str = Field(...)
    KEYCLOAK_CLIENT_SECRET: str = Field(...)
    KEYCLOAK_ADMIN_USER: str = Field(...)
    KEYCLOAK_ADMIN_PASSWORD: str = Field(...)
    NATS_URL: str = Field(...)

    model_config = SettingsConfigDict(extra="ignore")