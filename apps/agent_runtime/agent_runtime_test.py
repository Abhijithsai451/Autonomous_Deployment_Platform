from uuid import uuid4
import pytest
from sqlalchemy.orm import Session

from apps.agent_runtime.application.event_handlers import handle_task_ready_event
from apps.agent_runtime.infrastructure.database import agent_db_session
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository
from apps.agent_runtime.repository.outbox_repository import OutboxRepository
from apps.agent_runtime.repository.processed_events_repository import ProcessedEventsRepository
from apps.agent_runtime.tools.tool_registry import ToolRegistryError, global_tool_registry, ToolRegistry


@pytest.fixture
def db():
    db_gen = agent_db_session()
    session = next(db_gen)
    try:
        yield session
    finally:
        db_gen.close()


@pytest.fixture
def task_event_data():
    event_id = uuid4()
    task_id = uuid4()
    workflow_instance_id = uuid4()

    payload = {
        "event_id": str(event_id),
        "task_id": str(task_id),
        "workflow_instance_id": str(workflow_instance_id),
        "agent_slug": "test-agent-1",
        "input_data": {
            "action_type": "execute",
            "input_reference": str(uuid4()),
            "payload": {"test_key": "test_value"},
        },
    }

    metadata = {
        "event_id": str(event_id),
        "event_type": "workflow.events.task.ready",
    }

    return {
        "event_id": event_id,
        "task_id": task_id,
        "workflow_instance_id": workflow_instance_id,
        "payload": payload,
        "metadata": metadata,
    }


def test_vertical_slice_event_processing(db: Session, task_event_data: dict):
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]
    task_id = task_event_data["task_id"]
    event_id = task_event_data["event_id"]

    logger.info("Executing Test 1: Processing new task event...", event_id=str(event_id))

    # 1. Execute Event Handler
    success = handle_task_ready_event(db=db, payload=payload, metadata=metadata)
    assert success is True, "Event processing returned False instead of True"

    run_repo = AgentRunsRepository(db)
    outbox_repo = OutboxRepository(db)
    processed_repo = ProcessedEventsRepository(db)
    logger.info("Verified DB Assertions")

    # 2. Verify AgentRun Record
    run = run_repo.get_by_task_id(task_id)
    assert run is not None, "AgentRun record was not created in the database."

    run_status_str = run.status.value if hasattr(run.status, "value") else str(run.status)
    assert run_status_str == "COMPLETED", f"Expected COMPLETED status, got '{run.status}'."
    assert run.output_data.get("message").lower() == "testagent executed successfully"
    logger.info("Assertion Passed: AgentRun created with COMPLETED status.", run_id=str(run.id))

    is_processed = processed_repo.is_processed(
        event_id=event_id,
        consumer_group="agent-runtime-task-consumer"
    )
    assert is_processed is True, "Event was not recorded in processed_events table."
    logger.info("Assertion Passed: ProcessedEvent Record Verified")

    outbox_event = outbox_repo.get_latest_by_aggregate(run.id)
    assert outbox_event is not None, "Outbox event was not created."

    actual_event_type = outbox_event.event_type.value if hasattr(outbox_event.event_type, "value") else str(outbox_event.event_type)
    actual_status = outbox_event.status.value if hasattr(outbox_event.status, "value") else str(outbox_event.status)

    assert actual_event_type.strip() == "agent_runtime.events.agent.finished", f"Unexpected event_type: '{actual_event_type}'"
    assert actual_status in ("PENDING", "PUBLISHED"), f"Unexpected outbox status: '{actual_status}'"

    logger.info("Assertion Passed: OutboxEvent verified.", outbox_id=str(outbox_event.id))
    logger.info("Assertion Passed: Event pipeline executed successfully.")


def test_vertical_slice_duplicate_event_handling(db: Session, task_event_data: dict):
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]
    event_id = task_event_data["event_id"]

    logger.info("Executing Test 2: Simulating duplicate event retry...", event_id=str(event_id))

    # Initial Run
    first_pass = handle_task_ready_event(db=db, payload=payload, metadata=metadata)
    assert first_pass is True

    # Duplicate Retry
    duplicate_pass = handle_task_ready_event(db=db, payload=payload, metadata=metadata)
    assert duplicate_pass is True, "Duplicate event handling failed."
    logger.info("Assertion Passed: Duplicate Event safely ignored.")

@pytest.fixture
def registry():
    """Provides a fresh instance of ToolRegistry populated with default tools."""
    return ToolRegistry()


def test_default_tools_and_schemas_registered(registry):
    """Verify that default local tools are registered and return correct schemas."""
    schemas = registry.get_all_schemas()
    registered_names = [s["name"] for s in schemas]

    assert "json_transformer" in registered_names
    assert "task_reader" in registered_names
    assert len(schemas) == 2


def test_json_transformer_tool_execution(registry):
    """Verify successful execution, key filtering, and key remapping for JSONTransformerTool."""
    transform_input = {
        "data": {
            "user_id": 123,
            "email_address": "test@cortexops.ai",
            "internal_flag": True,
        },
        "select_keys": ["user_id", "email_address"],
        "remap_keys": {"email_address": "user_email"},
    }

    result = registry.execute_tool(
        tool_name="json_transformer",
        parameters=transform_input,
        context_metadata={"execution_source": "pytest_phase3"},
    )

    assert result.success is True
    assert result.error is None
    assert result.result["transformed_data"] == {
        "user_id": 123,
        "user_email": "test@cortexops.ai",
    }
    assert result.result["keys_processed"] == 2
    assert result.execution_duration_ms > 0.0


def test_task_reader_tool_validation_failure(registry):
    """Verify safe error handling boundary when required parameters are missing."""
    invalid_input = {
        "payload": {"action": "deploy"},
        "required_fields": ["action", "target_env"],  # 'target_env' is missing
    }

    result = registry.execute_tool(
        tool_name="task_reader",
        parameters=invalid_input,
    )

    assert result.success is False
    assert result.result is None
    assert "Missing required fields" in result.error
    assert "target_env" in result.error


def test_unregistered_tool_resolution_raises_error(registry):
    """Verify that resolving an unregistered tool name raises ToolRegistryError."""
    with pytest.raises(ToolRegistryError) as exc_info:
        registry.resolve("non_existent_tool")

    assert "Tool 'non_existent_tool' is not registered" in str(exc_info.value)


def test_global_tool_registry_instance():
    """Verify global registry singleton is instantiated and contains standard tools."""
    tool = global_tool_registry.get("json_transformer")
    assert tool is not None
    assert tool.name == "json_transformer"