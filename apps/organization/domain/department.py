import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, UUID, ForeignKey, String, Enum, Text, JSON, DateTime
from sqlalchemy.orm import relationship

from apps.organization.infrastructure.base import Base

class DepartmentType(PyEnum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    SRE = "SRE"
    SUPPORT = "SUPPORT"
class DepartmentStatus(PyEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"

class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema":"departments"}

    id = Column(UUID(as_uuid=True), primary_key = True, default= uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.organizations.id"), nullable = False)
    name = Column(String(255), nullable = False)
    type = Column(Enum(DepartmentType, name = "department_type", schema = "organization"),
                  default = DepartmentType.INTERNAL,nullable = False )
    status = Column(Enum(DepartmentStatus, name="department_status", schema="organization"), default=DepartmentStatus.CREATED,
                   nullable=False)
    description = Column(Text, nullable = True)
    metadata = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    organization = relationship("organizations", back_populates="departments")