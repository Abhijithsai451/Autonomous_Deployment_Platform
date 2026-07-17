from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from packages.config.settings import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



