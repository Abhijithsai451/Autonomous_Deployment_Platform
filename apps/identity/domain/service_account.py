from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from apps.identity.infrastructure.base import Base

class ServiceAccount(Base):
    __tablename__ = "service_accounts"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)