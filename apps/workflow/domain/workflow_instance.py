import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, UUID, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from apps.workflow.infrastructure.base import Base

class WorkflowStatus(PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = {"schema": "workflow"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    blueprint_id = Column(UUID(as_uuid=True), ForeignKey("workflow.workflow_blueprints.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(WorkflowStatus, name="workflow_status", schema="workflow"), default=WorkflowStatus.PENDING, nullable=False)
    current_step = Column(String(100), nullable=True)
    started_by = Column(UUID(as_uuid=True), nullable=True)
    temporal_workflow_id = Column(String(255), nullable=True)
    temporal_run_id = Column(String(255), nullable=True)
    input_data = Column(JSONB, default={}, nullable=True)
    output_data = Column(JSONB, default={}, nullable=True)
    error_details = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    blueprint = relationship("WorkflowBlueprint", back_populates="instances")
    tasks = relationship("Task", back_populates="workflow_instance", cascade="all, delete-orphan")
    events = relationship("WorkflowEvent", back_populates="workflow_instance", cascade="all, delete-orphan")
