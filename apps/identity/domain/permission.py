from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()
class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String, nullable=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
