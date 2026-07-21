from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ORGANIZATION_DATABASE_URL: str
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_CLIENT_SECRET: str
    KEYCLOAK_ADMIN_USER: str
    KEYCLOAK_ADMIN_PASSWORD: str
    NATS_URL : str

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )

org_settings = Settings()
