from apps.agent_runtime.application.execution_service import ExecutionService
from apps.agent_runtime.infrastructure.database import agent_db_session
from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client as nats


class TaskReadyWorker:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True

        async def nats_event_handler(payload: dict, metadata: dict):
            async with agent_db_session() as session:
                await ExecutionService.process_task_ready_event(session, payload, metadata)

        await nats.register_listener(
        subject = "workflow.events.task.ready",
        durable_name = "agent_runtime_task_ready_consumer",
        handler = nats_event_handler,
        stream = "workflow_events"
        )