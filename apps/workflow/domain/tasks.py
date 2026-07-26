from datetime import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, UUID, String, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from apps.workflow.infrastructure.base import Base

class TaskStatus(PyEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "workflow"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_instance_id = Column(UUID(as_uuid=True), ForeignKey("workflow.workflow_instances.id", ondelete="CASCADE"),
                                  nullable=False)
    task_definition_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    action_type = Column(String(100), nullable=False)
    status = Column(Enum(TaskStatus, name="task_status", schema="workflow"), default=TaskStatus.PENDING, nullable=False)
    assigned_agent_id = Column(UUID(as_uuid=True), nullable=True)
    input_data = Column(JSONB, default={}, nullable=True)
    output_data = Column(JSONB, default={}, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workflow_instance = relationship("WorkflowInstance", back_populates="tasks")
    events = relationship("WorkflowEvent", back_populates="task")

    dependencies = relationship(
        "Task",
        secondary="workflow.task_dependencies",
        primaryjoin="Task.id == TaskDependency.task_id",
        secondaryjoin="Task.id == TaskDependency.depends_on_task_id",
        backref="depended_on_by",
        overlaps="depended_on_by"
    )