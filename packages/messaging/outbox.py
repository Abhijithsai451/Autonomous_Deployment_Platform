import asyncio
from typing import Generator, Callable, Any

from sqlalchemy.orm import Session

from packages.logging.structured_logs import  struc_logger as logger

MAX_OUTBOX_RETRIES = 5
class OutboxPublisher:
    def __init__(
            self,
            db_session_factory: Callable[[], Generator[Session, None, None]],
            event_bus: Any,
            outbox_model: Any,
            outbox_status_enum: Any,
            poll_interval_seconds: float = 1.0,
            batch_size: int = 50,
    ):
        self.db_session_factory = db_session_factory
        self.bus = event_bus
        self.outbox_model = outbox_model
        self.status_enum = outbox_status_enum
        self.poll_interval = poll_interval_seconds
        self.batch_size = batch_size
        self._is_running = False

    async def process_events(self) -> int:
        processed_count = 0
        db_gen = self.db_session_factory()
        db: Session = next(db_gen)

        try:
            events = (
                db.query(self.outbox_model)
                .filter(self.outbox_model.status == self.status_enum.PENDING)
                .order_by(self.outbox_model.created_at.asc())
                .limit(self.batch_size)
                .with_for_update(skip_locked=True)
                .all()
            )

            if not events:
                return 0

            for event in events:
                try:
                    await self.bus.publish(
                        event_type=event.event_type,
                        payload=event.payload
                    )

                    if hasattr(event, "mark_processed"):
                        event.mark_processed()
                    else:
                        event.status = self.status_enum.PROCESSED

                    processed_count += 1

                except Exception as exc:
                    if hasattr(event, "mark_failed"):
                        event.mark_failed(str(exc), max_retries=MAX_OUTBOX_RETRIES)
                    else:
                        current_retries = getattr(event, "retry_count", 0) + 1
                        event.retry_count = current_retries
                        event.error_message = str(exc)
                        if current_retries >= MAX_OUTBOX_RETRIES:
                            event.status = self.status_enum.DEAD_LETTER
                        else:
                            event.status = self.status_enum.PENDING

                    if event.status in (self.status_enum.DEAD_LETTER, self.status_enum.FAILED):
                        logger.error(f"Outbox event {event.id} reached max retries. Sent to DLQ: {exc}")
                        try:
                            await self.bus.publish(
                                event_type="dlq.events",
                                payload={
                                    "original_event_id": str(event.id),
                                    "event_type": event.event_type,
                                    "payload": event.payload,
                                    "error": str(exc),
                                    "failed_after_retries": event.retry_count,
                                }
                            )
                        except Exception as dlq_exc:
                            logger.error(f"Failed to publish to DLQ topic: {dlq_exc}")
                    else:
                        logger.warning(
                            f"Failed outbox attempt {event.retry_count}/{MAX_OUTBOX_RETRIES} for event {event.id}: {exc}"
                        )

            db.commit()
        except Exception as err:
            db.rollback()
            logger.error(f"Error processing outbox batch: {err}")
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        return processed_count



    async def start(self) -> None:
        self._is_running = True
        logger.info("Outbox Publisher Worker started.")
        while self._is_running:
            try:
                count = await self.process_events()
                if count == 0:
                    await asyncio.sleep(self.poll_interval)
                else:
                    await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Unexpected error in outbox loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._is_running = False
        logger.info("Outbox Publisher Worker stopping...")