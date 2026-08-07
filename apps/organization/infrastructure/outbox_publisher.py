from apps.organization.domain.outbox import OutboxEvent, OutboxStatus
from apps.organization.infrastructure.database import org_db_session
from apps.organization.infrastructure.org_nats_client import org_nats_client
from packages.messaging.outbox import OutboxPublisher


class IdentityOutboxPublisher(OutboxPublisher):
    def __init__(self, poll_interval_seconds: float = 0.01, batch_size = 50):
        super().__init__(
            db_session_factory=org_db_session,
            event_bus = org_nats_client,
            outbox_model=OutboxEvent,
            outbox_status_enum=OutboxStatus,
            poll_interval_seconds=poll_interval_seconds,
            batch_size=batch_size
        )
