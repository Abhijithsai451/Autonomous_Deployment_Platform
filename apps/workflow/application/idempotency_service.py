import functools
from typing import Callable, Dict, Any, Awaitable

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.workflow.infrastructure.database import workflow_db_session
from apps.workflow.infrastructure.structured_logs import struct_logger as logger

class IdempotencyService:
    def __init__(self, db:Session):
        self.db = db

    def is_already_processed(self, event_id: str, consumer_group: str) -> bool:
        result = self.db.execute(
            text("""
                 SELECT 1
                 FROM workflow.processed_events
                 WHERE event_id = :event_id
                   AND consumer_group = :consumer_group
                 """),
            {"event_id": str(event_id), "consumer_group": consumer_group}
        ).fetchone()
        return result is not None

    def mark_processed(self, event_id: str, consumer_group: str) -> None:
        """Records an event ID as processed within the active transaction."""
        self.db.execute(
            text("""
                INSERT INTO workflow.processed_events (event_id, consumer_group)
                VALUES (:event_id, :consumer_group)
                ON CONFLICT (event_id) DO NOTHING
            """),
            {"event_id": str(event_id), "consumer_group": consumer_group}
        )
def idempotent_listener(consumer_group: str):
    """
    Decorator/Wrapper for NATS handlers to enforce idempotency.
    """
    def decorator(handler: Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]):

        @functools.wraps(handler)
        async def wrapper(payload: Dict[str, Any], metadata: Dict[str, Any]) -> None:
            # Extract Event ID (check payload first, fallback to metadata)
            event_id = str(payload.get("id") or metadata.get("message_id") or "")

            if not event_id:
                # If message has no ID, execute handler normally
                await handler(payload, metadata)
                return

            db = workflow_db_session()
            try:
                idempotency_svc = IdempotencyService(db)

                if idempotency_svc.is_already_processed(event_id, consumer_group):
                    logger.info(
                        f"Skipping duplicate event processing.",
                        extra={"event_id": event_id, "consumer_group": consumer_group}
                    )
                    return
                await handler(payload, metadata)

                idempotency_svc.mark_processed(event_id, consumer_group)
                db.commit()

            except Exception as exc:
                db.rollback()
                logger.error(f"Error handling idempotent NATS event {event_id}: {exc}")
                raise exc
            finally:
                try:
                    next(db)
                except (StopIteration, TypeError):
                    pass

        return wrapper
    return decorator
