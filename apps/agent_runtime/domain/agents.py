import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Enum, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID

from apps.agent_runtime.infrastructure.base import Base

class AgentType(enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"

class AgentStatus(enum.Enum):
    READY = "READY"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    FINISHED = "FINISHED"

class Agents(Base):
    __tablename__ = "agents"
    __table_args__ = (
        {"schema": "agent_runtime"}
    )

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid4)
    name = Column(String(150), nullable = False)
    type = Column(Enum(AgentType, name = "agent_type", schema = "agent_runtime"), default = AgentType.ACTIVE, index = True,)
    status = Column(Enum(AgentStatus, name="agent_type", schema="agent_runtime"), default=AgentStatus.READY, index=True )
    configuration = Column(JSON, default={}, nullable = False)
    created_at = Column(DateTime(timezone=True), default = datetime.utc.now, nullable = False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utc.now)



