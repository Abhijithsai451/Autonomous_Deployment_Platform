from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, UUID, ForeignKey, Boolean, String, DateTime, Table
from sqlalchemy.orm import relationship
from apps.identity.infrastructure.base import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("identity.roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("identity.permissions.id", ondelete="CASCADE"), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("identity.organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    system_role = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    permissions = relationship("Permission", secondary=role_permissions)

