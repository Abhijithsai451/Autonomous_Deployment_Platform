from apps.identity.config.identity_settings import identity_settings as settings
from packages.database.client import DatabaseClient

db_client = DatabaseClient(
    database_url = settings.IDENTITY_DATABASE_URL,
    schema_name = "identity"
)

get_db_session = db_client.get_session