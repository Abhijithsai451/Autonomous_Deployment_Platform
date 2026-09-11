from packages.config.services.workflow import WorkflowServiceSettings

_settings = WorkflowServiceSettings()

class WorkflowSettingsAdapter():
    def __init__(self, config: WorkflowServiceSettings) -> None:
        self._config = config

    @property
    def WORKFLOW_DATABASE_URL(self) -> str:
        return self._config.WORKFLOW_DATABASE_URL

    @property
    def NATS_URL(self) -> str:
        return self._config.NATS_URL

workflow_settings = WorkflowSettingsAdapter(_settings)