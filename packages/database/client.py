from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session


class DatabaseClient:
    """
    Database client to connect to the database for microservice.
    """
    def __init__(self, database_url: str, schema_name: str):
        self.database_url = database_url
        self.schema_name = schema_name

        self.engine = create_engine(
            self.database_url,
            connect_args={"options": f"-c search_path={self.schema_name}"}
        )

        self.SessionLocal = sessionmaker(
            autocommit = False,
            autoflush = False,
            bind = self.engine
        )

    def init_schema(self)-> None:
        """Ensures the private schema namespace exists"""
        with self.engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))

    def get_session(self)-> Generator[Session, None, None]:
        """Dependency Provider for FastAPI route injection"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()