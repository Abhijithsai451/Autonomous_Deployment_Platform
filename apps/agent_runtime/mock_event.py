import asyncio
import uuid

from infrastructure.nats.event_bus import EventBus


async def publish_mock_event():
    workflow_event_bus = EventBus(service = "workflow")
    await workflow_event_bus.initialize()
    dummy_event_id = str(uuid.uuid4())
    dummy_task_id = str(uuid.uuid4())
    dummy_workflow_id = str(uuid.uuid4())

    payload = {
        "event_id": dummy_event_id,
        "task_id": dummy_task_id,
        "workflow_instance_id": dummy_workflow_id,
        "agent_slug": "test-agent-1",
        "input_data": {
            "message": "Hello CortexOps Phase 1!"
        }
    }

    print("Publishing dummy 'workflow.events.task.ready' event...")
    await workflow_event_bus.publish(
        event_type="events.task.ready",
        payload=payload
    )

if __name__ == "__main__":
    asyncio.run(publish_mock_event())