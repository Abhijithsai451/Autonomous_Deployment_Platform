from packages.database.client import DatabaseClient
from apps.workflow.config import workflow_settings as settings
workflow_db_client = DatabaseClient(
    database_url = settings.WORKFLOW_DATABASE_URL,
    schema_name = "workflow"
)

workflow_db_session = workflow_db_client.get_session