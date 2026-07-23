from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    NATS_URL: str
    model_config = SettingsConfigDict(
        env_file = None,
        extra = "ignore"
    )

common_settings = Settings()
