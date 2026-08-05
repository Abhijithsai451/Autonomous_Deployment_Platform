from apps.identity.domain.domain import OutboxEvent, OutboxStatus
from apps.identity.infrastructure.database import identity_db_session
from apps.identity.infrastructure.identity_nats_client import identity_nats_client
from packages.messaging.outbox import OutboxPublisher


class IdentityOutboxPublisher(OutboxPublisher):
    def __init__(self, poll_interval_seconds: float = 0.01, batch_size = 50):
        super().__init__(
            db_session_factory=identity_db_session,
            event_bus = identity_nats_client,
            outbox_model=OutboxEvent,
            outbox_status_enum=OutboxStatus,
            poll_interval_seconds=poll_interval_seconds,
            batch_size=batch_size
        )
