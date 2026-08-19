import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.agent_runtime.application.execution_service import ExecutionService
from apps.agent_runtime.domain.agent_runs import RunStatus
from apps.agent_runtime.domain.outbox import OutboxStatus


@pytest.mark.asyncio
async def test_process_task_ready_event_success():
    """Unit test for process_task_ready_event logic."""

    mock_db = MagicMock()

    mock_db.execute.return_value.scalar_one_or_none.side_effect = [
        None,
    ]

    mock_agent = MagicMock()
    mock_agent.id = uuid.uuid4()
    mock_agent.slug = "test-agent-1"
    mock_agent.status = "ACTIVE"
    mock_agent.run_agent.return_value = "Hello -> Agent Run"

    mock_db.execute.return_value.scalars.return_value.first.return_value = mock_agent

    test_event_id = str(uuid.uuid4())
    test_task_id = str(uuid.uuid4())
    test_workflow_id = str(uuid.uuid4())

    payload = {
        "event_id": test_event_id,
        "task_id": test_task_id,
        "workflow_instance_id": test_workflow_id,
        "agent_slug": "test-agent-1",
        "input_data": {
            "message": "Unit Test Message"
        }
    }
    metadata = {"headers": {"Nats-Msg-Id": test_event_id}}

    await ExecutionService.process_task_ready_event(mock_db, payload, metadata)

    assert mock_db.add.call_count == 3

    added_entities = [call.args[0] for call in mock_db.add.call_args_list]

    agent_run = added_entities[0]
    processed_event = added_entities[1]
    outbox_event = added_entities[2]

    assert agent_run.task_id == uuid.UUID(test_task_id)
    assert agent_run.workflow_instance_id == uuid.UUID(test_workflow_id)
    assert agent_run.status == RunStatus.COMPLETED
    assert agent_run.output_data["echo_message"] == "Unit Test Message"
    assert agent_run.output_data["agent_response"] == "Hello -> Agent Run"

    assert processed_event.event_id == uuid.UUID(test_event_id)
    assert processed_event.consumer_group == "agent-runtime-task-ready-consumer"

    assert outbox_event.event_type == "agent.run.completed"
    assert outbox_event.status == OutboxStatus.PENDING
    assert outbox_event.payload["status"] == RunStatus.COMPLETED.value
    assert outbox_event.payload["task_id"] == test_task_id

    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_task_ready_event_idempotency_skip():
    """Unit test ensuring duplicate events are safely skipped."""

    mock_db = MagicMock()
    mock_existing_event = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_existing_event

    test_event_id = str(uuid.uuid4())
    payload = {
        "event_id": test_event_id,
        "task_id": str(uuid.uuid4()),
        "workflow_instance_id": str(uuid.uuid4()),
        "input_data": {}
    }

    await ExecutionService.process_task_ready_event(mock_db, payload, {})

    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()