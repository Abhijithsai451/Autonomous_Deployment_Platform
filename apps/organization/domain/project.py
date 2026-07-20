import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, UUID, ForeignKey, String, Text, JSON, DateTime, Enum
from sqlalchemy.orm import relationship

from apps.organization.infrastructure.base import Base
class ProjectStatus(PyEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema":"organization"}

    id = Column(UUID(as_uuid=True), primary_key = True, default = uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.organizations.id"), nullable = False)
    name = Column(String(255), nullable = False)
    description = Column(Text, nullable = True)
    lifecycle = Column(String(255),default = "ACTIVE", nullable = False)
    staus = Column(Enum(ProjectStatus, name="project_status",schema="organization"), default = ProjectStatus.CREATED, nullable=False)
    metadata = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    organization = relationship("organizations",back_populates="projects")



