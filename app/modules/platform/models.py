from  datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from sqlalchemy import JSON, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class Base(DeclarativeBase):
    type_annotation_map = {
        Dict[str, Any]: JSON
    }

class StatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class WorkflowModel(Base):
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(primary_key = True, default = uuid4)
    description: Mapped[str] = mapped_column(String(500))
    status: Mapped[StatusEnum] = mapped_column(default=StatusEnum.PENDING)

    temporal_workflow_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)

    context_payload: Mapped[Dict[str, Any]] = mapped_column(default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.timezone.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.timezone.utcnow, onupdate=datetime.timezone.utcnow)

    # Relationships
    tasks: Mapped[List["TaskModel"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))

    title: Mapped[str] = mapped_column(String(255))
    depends_on: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    assigned_agent: Mapped[str] = mapped_column(String(100))
    status: Mapped[StatusEnum] = mapped_column(default=StatusEnum.PENDING)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.timezone.utcnow)

    # Relationships
    workflow: Mapped["WorkflowModel"] = relationship(back_populates="tasks")
    steps: Mapped[List["AgentStepModel"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class AgentStepModel(Base):
    __tablename__ = "agent_steps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))

    agent_name: Mapped[str] = mapped_column(String(100))
    thought: Mapped[Optional[str]] = mapped_column(String)  # The LLM reasoning trace

    # Detailed logs of structured data
    tool_calls: Mapped[Optional[Dict[str, Any]]] = mapped_column(default=dict, nullable=True)
    token_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(default=dict,
                                                                    nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.timezone.utcnow)

    # Relationships
    task: Mapped["TaskModel"] = relationship(back_populates="steps")