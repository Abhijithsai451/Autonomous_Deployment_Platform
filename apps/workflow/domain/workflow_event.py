from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, UUID, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from apps.workflow.infrastructure.base import Base

class WorkflowEvent(Base):
    __tablename__ = "workflow_events"
    __table_args__ = {"schema": "workflow"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_instance_id = Column(UUID(as_uuid=True), ForeignKey("workflow.workflow_instances.id", ondelete="CASCADE"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("workflow.tasks.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, default={}, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    workflow_instance = relationship("WorkflowInstance", back_populates="events")
    task = relationship("Task", back_populates="events")