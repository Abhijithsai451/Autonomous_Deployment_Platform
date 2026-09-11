from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentRuntimeServiceSettings(BaseSettings):
    AGENT_RUNTIME_DATABASE_URL: str
    NATS_URL: str
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)

    model_config = SettingsConfigDict( extra="ignore")