from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID

from apps.agent_runtime.infrastructure.base import Base


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    __table_args__ = (
        UniqueConstraint("event_id", "consumer_group", name="uq_event_consumer"),
        {"schema": "agent_runtime"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    consumer_group = Column(String(100), nullable=False)
    processed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )