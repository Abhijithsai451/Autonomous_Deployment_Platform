from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class NatsSettings(BaseSettings):
    NATS_URL: str = Field(default="nats://localhost:4222", description="NATS connection URL")
    NATS_CONNECTION_TIMEOUT: int = Field(default=5, description="Timeout in seconds")
    NATS_MAX_RECONNECT_ATTEMPTS: int = Field(default=10, description="Max reconnection retries")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")