import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Enum, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID

from apps.agent_runtime.infrastructure.base import Base

class AgentStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"

class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {"schema": "agent_runtime"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(150), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(Enum(AgentStatus, name="agent_status", schema="agent_runtime"), default=AgentStatus.ACTIVE, nullable=False)
    configuration = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)






