from apps.agent_runtime.config.settings import agent_runtime_settings
from packages.database.client import DatabaseClient

agent_runtime_db_client = DatabaseClient(
    database_url = agent_runtime_settings.AGENT_RUNTIME_DATABASE_URL,
    schema_name= "agent_runtime"
)

agent_db_session = agent_runtime_db_client.get_session