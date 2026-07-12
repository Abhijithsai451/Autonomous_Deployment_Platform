from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str = "CortexOps"
    KEYCLOAK_CLIENT_ID: str = "identity-service"
    KEYCLOAK_CLIENT_SECRET: str
    KEYCLOAK_ADMIN_USER: str
    KEYCLOAK_ADMIN_PASSWORD: str

    class Config:
        env_file = ".env"

settings = Settings()
