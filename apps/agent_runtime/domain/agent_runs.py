import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, UUID, ForeignKey, Enum, JSON, Text, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import JSONB

from apps.agent_runtime.infrastructure.base import Base


class RunStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

class AgentRuns(Base):
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "agent_runtime"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_runtime.agents.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    workflow_instance_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(
        Enum(RunStatus, name="run_status", schema="agent_runtime"),
        default=RunStatus.PENDING,
        nullable=False,
        index=True
    )
    input_data = Column(JSONB, default={}, nullable=False)
    output_data = Column(JSONB, nullable=True)
    error = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    duration_ms = Column(BigInteger, default=0, nullable=True)