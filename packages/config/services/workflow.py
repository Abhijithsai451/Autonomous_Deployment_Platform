from pydantic_settings import SettingsConfigDict, BaseSettings


class WorkflowServiceSettings(BaseSettings):
    WORKFLOW_DATABASE_URL: str
    NATS_URL: str

    model_config = SettingsConfigDict( extra="ignore")