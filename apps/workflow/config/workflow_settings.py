from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    WORKFLOW_DATABASE_URL: str
    NATS_URL : str

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )

workflow_settings = Settings()
