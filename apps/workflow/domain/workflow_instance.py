from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, UUID, String, DateTime, Enum, ForeignKey, INT
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from apps.workflow.domain.exceptions import InvalidStateTransitionError
from apps.workflow.infrastructure.base import Base

class WorkflowStatus(PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = {"schema": "workflow"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    blueprint_id = Column(UUID(as_uuid=True), ForeignKey("workflow.workflow_blueprints.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(WorkflowStatus, name="workflow_status", schema="workflow"), default=WorkflowStatus.PENDING, nullable=False)
    version = Column(INT, default=1, nullable=False)
    current_step = Column(String(100), nullable=True)
    started_by = Column(UUID(as_uuid=True), nullable=True)
    temporal_workflow_id = Column(String(255), nullable=True)
    temporal_run_id = Column(String(255), nullable=True)
    input_data = Column(JSONB, default={}, nullable=True)
    output_data = Column(JSONB, default={}, nullable=True)
    error_details = Column(JSONB, nullable=True)
    triggered_by = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


    blueprint = relationship("WorkflowBlueprint", back_populates="instances")
    tasks = relationship("Task", back_populates="workflow_instance", cascade="all, delete-orphan")
    events = relationship("WorkflowEvent", back_populates="workflow_instance", cascade="all, delete-orphan")


    # ========================================================
    # STATE MACHINE METHODS
    # ========================================================
    def start(self)-> None:
        """Transitions state from PENDING -> RUNNING."""
        if self.status != WorkflowStatus.PENDING:
            raise InvalidStateTransitionError("WorkflowInstance",str(self.id), self.status.value, "start")
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def pause(self) -> None:
        """Transitions state from RUNNING -> PAUSED."""
        if self.status != WorkflowStatus.RUNNING:
            raise InvalidStateTransitionError("WorkflowInstance", str(self.id), self.status.value, "pause")

        self.status = WorkflowStatus.PAUSED

    def resume(self) -> None:
        """Transitions state from PAUSED -> RUNNING."""
        if self.status != WorkflowStatus.PAUSED:
            raise InvalidStateTransitionError("WorkflowInstance", str(self.id), self.status.value, "resume")

        self.status = WorkflowStatus.RUNNING

    def complete(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Transitions state from RUNNING -> COMPLETED."""
        if self.status != WorkflowStatus.RUNNING:
            raise InvalidStateTransitionError("WorkflowInstance", str(self.id), self.status.value, "complete")

        self.status = WorkflowStatus.COMPLETED
        if output_data is not None:
            self.output_data = output_data
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Transitions state from RUNNING -> FAILED."""
        if self.status != WorkflowStatus.RUNNING:
            raise InvalidStateTransitionError("WorkflowInstance", str(self.id), self.status.value, "fail")

        self.status = WorkflowStatus.FAILED
        if error_details is not None:
            self.error_details = error_details
        self.completed_at = datetime.now(timezone.utc)

    def cancel(self, reason: str = "User cancelled execution") -> None:
        """Transitions state from PENDING, RUNNING, or PAUSED -> CANCELLED."""
        cancellable_states = {WorkflowStatus.PENDING, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED}
        if self.status not in cancellable_states:
            raise InvalidStateTransitionError("WorkflowInstance", str(self.id), self.status.value, "cancel")

        self.status = WorkflowStatus.CANCELLED
        self.error_details = {"cancellation_reason": reason}
        self.completed_at = datetime.now(timezone.utc)

    def timeout(self, reason: str = "Execution timed out") -> None:
        """Transitions state from RUNNING -> TIMED_OUT."""
        if self.status != WorkflowStatus.RUNNING:
            raise InvalidStateTransitionError("WorkflowInstance", str(self.id), self.status.value, "timeout")

        self.status = WorkflowStatus.TIMED_OUT
        self.error_details = {"timeout_reason": reason}
        self.completed_at = datetime.now(timezone.utc)