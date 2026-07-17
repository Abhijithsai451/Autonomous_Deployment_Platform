from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from apps.identity.infrastructure.database import Base

class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("identity.organizations.id"), nullable=False)
    service_account_id = Column(UUID(as_uuid=True), ForeignKey("identity.service_accounts.id"), nullable=True)
    name = Column(String(100), nullable=False)
    hashed_key = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)