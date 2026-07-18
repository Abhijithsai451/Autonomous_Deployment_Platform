from packages.config.settings import settings
from packages.database.client import DatabaseClient

db_client = DatabaseClient(
    database_url = settings.DATABASE_URL,
    schema_name = "identity"
)

get_db_session = db_client.get_session()