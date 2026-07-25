import datetime
from uuid import uuid4
from sqlalchemy import Column, UUID, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from apps.workflow.infrastructure.base import Base

class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
        CheckConstraint("task_id <> depends_on_task_id", name="chk_no_self_dependency"),
        {"schema": "workflow"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("workflow.tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("workflow.tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
