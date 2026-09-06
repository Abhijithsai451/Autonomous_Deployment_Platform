from apps.agent_runtime.domain.outbox import OutboxEvent, OutboxStatus
from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client
from apps.agent_runtime.infrastructure.database import agent_db_session
from packages.messaging.outbox import OutboxPublisher

class AgentRuntimeOutboxPublisher(OutboxPublisher):
    def __init__(self, poll_interval_seconds: float = 0.01, batch_size: int = 50):
        super().__init__(
            db_session_factory= agent_db_session,
            event_bus = agent_nats_client,
            outbox_model = OutboxEvent,
            outbox_status_enum=OutboxStatus,
            poll_interval_seconds=poll_interval_seconds,
            batch_size=batch_size
        )

agent_outbox_publisher = AgentRuntimeOutboxPublisher(poll_interval_seconds=0.01)