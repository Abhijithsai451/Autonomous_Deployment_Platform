from packages.database.client import DatabaseClient
from apps.workflow.config.workflow_settings import workflow_settings

workflow_db_client = DatabaseClient(
    database_url = workflow_settings.WORKFLOW_DATABASE_URL,
    schema_name = "workflow"
)

workflow_db_session = workflow_db_client.get_session