import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Enum, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from apps.identity.infrastructure.base import Base

class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"

class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "workflow"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(
        Enum(OutboxStatus, name="outbox_status", schema="workflow"),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True
    )
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def mark_processed(self) -> None:
        self.status = OutboxStatus.PROCESSED
        self.processed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.retry_count += 1
        self.error_message = error
        if self.retry_count >= 5:
            self.status = OutboxStatus.FAILED
        else:
            self.status = OutboxStatus.PENDING
