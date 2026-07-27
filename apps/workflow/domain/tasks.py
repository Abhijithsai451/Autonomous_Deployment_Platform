from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, UUID, String, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.infrastructure.base import Base

class TaskStatus(PyEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"

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

    # ========================================================
    # STATE MACHINE METHODS
    # ========================================================

    def mark_ready(self) -> None:
        """Transitions state from PENDING or RETRYING -> READY."""
        allowed_states = {TaskStatus.PENDING, TaskStatus.RETRYING}
        if self.status not in allowed_states:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "mark_ready")

        self.status = TaskStatus.READY

    def start(self) -> None:
        """Transitions state from READY -> RUNNING."""
        if self.status != TaskStatus.READY:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "start")

        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Transitions state from RUNNING -> COMPLETED."""
        if self.status != TaskStatus.RUNNING:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "complete")

        self.status = TaskStatus.COMPLETED
        if output_data is not None:
            self.output_data = output_data
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Transitions state from RUNNING -> FAILED."""
        if self.status != TaskStatus.RUNNING:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "fail")

        self.status = TaskStatus.FAILED
        if error_details is not None:
            self.error_details = error_details
        self.completed_at = datetime.now(timezone.utc)

    def retry(self) -> None:
        """Transitions state from FAILED -> RETRYING."""
        if self.status != TaskStatus.FAILED:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "retry")

        if self.retry_count >= self.max_retries:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "max_retries_exceeded")

        self.retry_count += 1
        self.status = TaskStatus.RETRYING

    def cancel(self, reason: str = "Task cancelled") -> None:
        """Transitions state from PENDING, READY, or RUNNING -> CANCELLED."""
        cancellable_states = {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING}
        if self.status not in cancellable_states:
            raise InvalidStateTransitionError("Task", str(self.id), self.status.value, "cancel")

        self.status = TaskStatus.CANCELLED
        self.error_details = {"cancellation_reason": reason}
        self.completed_at = datetime.now(timezone.utc)