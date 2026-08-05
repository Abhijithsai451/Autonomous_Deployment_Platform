from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, UUID, ForeignKey, Boolean, String, DateTime, Table, Text
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
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_role = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow,nullable=False)
    permissions = relationship("Permission", secondary=role_permissions)

