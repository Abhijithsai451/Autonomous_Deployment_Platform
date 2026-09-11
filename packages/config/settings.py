import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = os.getenv("ENV_FILE", str(BASE_DIR / ".env"))
class CommonSettings(BaseSettings):
    """
    Standardized CortexOps platform settings contract.
    Enforces fail-fast validation and secret safety across all microservices.
    """
    model_config = SettingsConfigDict(
        env_file=(ENV_FILE_PATH, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    # ------------------------------------------------------------------
    # Environment & Application Identity
    # ------------------------------------------------------------------
    CORTEXOPS_ENV: Literal["local", "dev", "staging", "prod"] = Field(
        default="local",
        description="Runtime environment identifier"
    )
    SERVICE_NAME: str = Field(
        default="cortexops-service",
        description="Name of the running microservice"
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag; enforced False in production"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # ------------------------------------------------------------------
    # PostgreSQL Configuration
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="cortexops", description="Database name")
    POSTGRES_USER: str = Field(default="postgres", description="Database user")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="Database password")
    POSTGRES_POOL_SIZE: int = Field(default=10, ge=1, description="SQLAlchemy connection pool size")
    POSTGRES_MAX_OVERFLOW: int = Field(default=20, ge=0, description="SQLAlchemy max pool overflow")
    POSTGRES_TIMEOUT: float = Field(default=10.0, gt=0, description="Connection timeout in seconds")

    @property
    def DATABASE_URL(self) -> str:
        """Constructs safe async PostgreSQL connection URI."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------
    # NATS JetStream Configuration
    # ------------------------------------------------------------------
    NATS_URL: str = Field(default="nats://localhost:4222", description="NATS broker endpoint")
    NATS_CONNECT_TIMEOUT: float = Field(default=5.0, gt=0, description="Connection timeout in seconds")
    NATS_MAX_RECONNECT_ATTEMPTS: int = Field(default=10, ge=1, description="Max reconnect attempts")
    NATS_RECONNECT_TIME_WAIT: float = Field(default=2.0, gt=0, description="Wait time between reconnects")

    # ------------------------------------------------------------------
    # Redis Configuration
    # ------------------------------------------------------------------
    REDIS_HOST: str = Field(default="localhost", description="Redis server host")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535, description="Redis server port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password if auth enabled")
    REDIS_DB: int = Field(default=0, ge=0, description="Redis database index")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=1, description="Max connection pool size")
    REDIS_TIMEOUT: float = Field(default=5.0, gt=0, description="Socket connection timeout")

    @property
    def REDIS_URL(self) -> str:
        """Constructs safe Redis connection URI."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ------------------------------------------------------------------
    # OpenTelemetry Configuration
    # ------------------------------------------------------------------
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="http://localhost:4317",
        description="OTLP collector endpoint"
    )
    OTEL_TRACES_SAMPLER_ARG: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Sampling ratio (0.0 to 1.0)"
    )
    OTEL_SDK_DISABLED: bool = Field(
        default=False,
        description="Flag to completely disable telemetry SDK"
    )

    # ------------------------------------------------------------------
    # Fail-Fast Validation Rules
    # ------------------------------------------------------------------
    @field_validator("DEBUG", mode="after")
    @classmethod
    def enforce_production_debug_off(cls, v: bool, info) -> bool:
        env = info.data.get("CORTEXOPS_ENV")
        if env == "prod" and v is True:
            raise ValueError("DEBUG mode must be disabled in 'prod' environment.")
        return v

    @field_validator("LOG_LEVEL", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return upper_v


# Singleton Instance available for packages
common_settings = CommonSettings()