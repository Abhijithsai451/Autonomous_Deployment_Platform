from uuid import uuid4

from sqlalchemy import Column, UUID, ForeignKey, Boolean, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()
class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("identity.organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    system_role = Column(Boolean, default=False)

