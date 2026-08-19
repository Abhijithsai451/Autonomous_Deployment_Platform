import asyncio
from contextlib import asynccontextmanager
from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client as nats
from apps.agent_runtime.infrastructure.database import agent_db_session
from apps.agent_runtime.infrastructure.outbox_publisher import AgentRuntimeOutboxPublisher
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.mock_event import publish_mock_event
from apps.agent_runtime.workers.event_worker import TaskReadyWorker


async def main():
    logger.info("Initializing the Agent Runtime Daemon ....")

    await nats.initialize()
    logger.info("NATS Core Messaging is successfully initialized for Agent Runtime Service")

    outbox_publisher = AgentRuntimeOutboxPublisher(poll_interval_seconds=0.01)
    asyncio.create_task(outbox_publisher.start())

    worker = TaskReadyWorker()
    await worker.start()
    logger.info("Agent Runtime is listening for events....")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        await outbox_publisher.stop()
        await nats.shutdown()
        logger.info("Phase 1 Execution run finished successfully ")


if __name__ == "__main__":
    asyncio.run(main())