from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AGENT_RUNTIME_DATABASE_URL: str
    NATS_URL : str
    REDIS_HOST : str
    REDIS_PORT : str

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )

agent_runtime_settings = Settings()