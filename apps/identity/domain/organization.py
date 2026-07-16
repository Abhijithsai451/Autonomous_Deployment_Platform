from enum import Enum as PyEnum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, UUID, String, Enum, JSON, DateTime
from sqlalchemy.orm import  relationship
from apps.identity.infrastructure.database import declarative_base
Base = declarative_base()

class OrgStatus(PyEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"

class OrgPlan(str, PyEnum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(Enum(OrgStatus), default=OrgStatus.ACTIVE, nullable=False)
    plan = Column(Enum(OrgPlan, native_enum=False), default=OrgPlan.FREE, nullable=False)
    settings = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    users = relationship("User", back_populates="organization", cascade = "all, delete-orphan")
