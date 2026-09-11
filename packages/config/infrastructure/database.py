from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(..., description="Database password - strictly required")
    POSTGRES_DB: str = Field(..., description="Target database name - strictly required")
    POSTGRES_POOL_SIZE: int = Field(default=10)
    POSTGRES_MAX_OVERFLOW: int = Field(default=20)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def connection_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"