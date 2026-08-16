import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, UUID, ForeignKey, Enum, JSON, Text, DateTime

from apps.agent_runtime.infrastructure.base import Base


class AgentStatus(enum.Enum):
    READY = "READY"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    FINISHED = "FINISHED"

class AgentRun(Base):
    __tablename__ = "agent_run"
    __table_args__ = {"schema": "agent_runtime"}

    id = Column(UUID(as_uuid= True),primary_key = True, default = uuid4 )
    agent_id = Column(UUID(as_uuid= True), ForeignKey("agent_runtime.agents.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid= True),  nullable=True)
    workflow_instance_id = Column(UUID(as_uuid= True), nullable=False)
    status = Column(Enum(AgentStatus, name="agent_status", schema="agent_runtime"), default=AgentStatus.READY, index=True)
    input_data = Column(JSON, default={}, nullable = False)
    output_data = Column(JSON, default=None, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
