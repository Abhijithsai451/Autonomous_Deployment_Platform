from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus
from apps.workflow.infrastructure.database import workflow_db_session
from apps.workflow.infrastructure.workflow_nats_client import workflow_nats_client
from packages.messaging.outbox import OutboxPublisher


class WorkflowOutboxPublisher(OutboxPublisher):
    def __init__(self, poll_interval_seconds: float = 0.01, batch_size: int = 50):
        super().__init__(
            db_session_factory=workflow_db_session,
            event_bus=workflow_nats_client,
            outbox_model=OutboxEvent,
            outbox_status_enum=OutboxStatus,
            poll_interval_seconds=poll_interval_seconds,
            batch_size=batch_size
        )
workflow_outbox_publisher = WorkflowOutboxPublisher()