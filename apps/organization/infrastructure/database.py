from apps.identity.config.identity_settings import identity_settings as settings
from packages.database.client import DatabaseClient

org_db_client = DatabaseClient(
    database_url = settings.ORGANIZATION_DATABASE_URL,
    schema_name = "organization"
)

org_db_session = org_db_client.get_session