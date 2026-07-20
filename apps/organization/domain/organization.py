import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Enum, JSON, DateTime
from sqlalchemy.orm import relationship

from apps.organization.infrastructure.base import Base


class OrgStatus(PyEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"

class OrgPlan(PyEnum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "organization"}

    id = Column(UUID(as_uuid=True), primary_key=True, default= uuid4)
    name = Column(String(255), nullable = False)
    slug = Column(String(100), unique=True, index=True, nullable=False)

    status = Column(Enum(OrgStatus, name="org_status",schema="organization"), default = OrgStatus.ACTIVE, nullable=False)
    general_settings = Column(JSON, default={}, nullable = False)
    security_settings = Column(JSON, default={}, nullable=False)
    llm_settings = Column(JSON, default={}, nullable=False)
    notification_settings = Column(JSON, default={}, nullable=False)
    billing_settings = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default = datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    projects = relationship("Projects", back_populates = "organizations", cascade="all, delete-orphan")
    departments = relationship("Departments", back_populates = "organization", cascade="all, delete-orphan")




