import datetime
from uuid import uuid4

from sqlalchemy import UniqueConstraint, Column, UUID, String, Integer, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from apps.workflow.infrastructure.base import Base


class WorkflowBlueprint(Base):
    __tablename__ = "workflow_blueprints"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_blueprint_name_version"),
        {"schema": "workflow"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    definition = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    instances = relationship("WorkflowInstance", back_populates="blueprint")



