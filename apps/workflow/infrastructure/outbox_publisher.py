import asyncio
from contextlib import contextmanager

from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus
from apps.workflow.infrastructure.database import workflow_db_session
from apps.workflow.infrastructure.workflow_nats_client import workflow_nats_client as nats
from apps.workflow.infrastructure.structured_logs import struct_logger as logger

class OutboxPublisher:
    def __init__(self, poll_interval_seconds: float = 1.0, batch_size: int = 50):
        self.poll_interval = poll_interval_seconds
        self.batch_size = batch_size
        self._is_running = False
        self.logger = logger

    async def process_pending_events(self) -> int:
        processed_count = 0
        db = workflow_db_session()
        try:
            events = (
                db.query(OutboxEvent)
                .filter(OutboxEvent.status == OutboxStatus.PENDING)
                .order_by(OutboxEvent.created_at.asc())
                .limit(self.batch_size)
                .with_for_update(skip_locked=True)
                .all()
            )

            if not events:
                return 0

            for event in events:
                try:
                    await nats.publish(event_type=event.event_type, payload=event.payload)
                    event.mark_processed()
                    processed_count += 1
                except Exception as exc:
                    self.logger.error(
                        f"Failed to publish outbox event {event.id}: {exc}",
                        extra={"event_id": str(event.id), "event_type": event.event_type}
                    )
                    event.mark_failed(error=str(exc))

            db.commit()
        except Exception as err:
            db.rollback()
            self.logger.error(f"Error processing outbox batch: {err}")
        finally:
            try:
                next(db)
            except StopIteration as e:
                pass

        return processed_count

    async def start(self) -> None:
        self._is_running = True
        logger.info("Outbox Publisher Worker started.")

        while self._is_running:
            try:
                count = await self.process_pending_events()
                if count == 0:
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Unexpected error in outbox loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._is_running = False
        logger.info("Outbox Publisher Worker stopping...")