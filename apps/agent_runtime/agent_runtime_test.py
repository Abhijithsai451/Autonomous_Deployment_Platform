from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from sqlalchemy import Text
from sqlalchemy.orm import Session

from apps.agent_runtime.application.event_handlers import handle_task_ready_event
from apps.agent_runtime.domain.agent_contract import AgentContext, AgentExecutionStatus
from apps.agent_runtime.domain.agents import Agent, AgentStatus
from apps.agent_runtime.infrastructure.database import agent_db_session
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.llm.base_client import BaseLLMClient, LLMResponse, ToolCall
from apps.agent_runtime.llm.llm_agent import ReActLLMAgent
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
def test_agent(db: Session):
    """Seed the database with a test agent using the repository helper."""
    # Call your new agentRepository helper function here
    agent = Agent(
        db=db,
        name="Test Agent",
        status = AgentStatus.ACTIVE,
    )
    if hasattr(agent, "slug"):
        agent.slug = "test-agent-1"

    db.add(agent)
    db.flush()
    return agent

@pytest.fixture
def task_event_data(test_agent: Agent):
    event_id = uuid4()
    task_id = uuid4()
    workflow_instance_id = uuid4()

    payload = {
        "event_id": str(event_id),
        "task_id": str(task_id),
        "workflow_instance_id": str(workflow_instance_id),
        "agent_slug": test_agent.slug,
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
        "agent_id": getattr(test_agent, "agent_id", getattr(test_agent, "id", None)),
    }


def test_vertical_slice_event_processing(db: Session, task_event_data: dict):
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]
    task_id = task_event_data["task_id"]
    event_id = task_event_data["event_id"]

    logger.info("Executing Test 1: Processing task event via ReAct Agent...", event_id=str(event_id))

    mock_llm_response = LLMResponse(
        content="Task processed successfully via ReAct loop.",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("apps.agent_runtime.application.event_handlers.OpenAILLMClient") as mock_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.generate.return_value = mock_llm_response
        mock_client_cls.return_value = mock_client_instance

        # 1. Execute Event Handler with mock API key
        success = handle_task_ready_event(
            db=db,
            payload=payload,
            metadata=metadata,
            api_key="mock-openai-key"
        )
        assert success is True, "Event processing returned False instead of True"

    run_repo = AgentRunsRepository(db)
    outbox_repo = OutboxRepository(db)
    processed_repo = ProcessedEventsRepository(db)

    # 2. Verify AgentRun Record State
    run = run_repo.get_by_task_id(task_id)
    assert run is not None, "AgentRun record was not created in the database."

    run_status_str = run.status.value if hasattr(run.status, "value") else str(run.status)
    assert run_status_str == "COMPLETED", f"Expected COMPLETED status, got '{run.status}'."
    assert "answer" in run.output_data
    assert run.output_data["answer"] == "Task processed successfully via ReAct loop."
    logger.info("Assertion Passed: AgentRun created with COMPLETED status and ReAct output.", run_id=str(run.id))

    # 3. Verify Idempotency Record
    is_processed = processed_repo.is_processed(
        event_id=event_id,
        consumer_group="agent-runtime-task-consumer"
    )
    assert is_processed is True, "Event was not recorded in processed_events table."

    # 4. Verify Outbox Staging
    outbox_event = outbox_repo.get_latest_by_aggregate(run.id)
    assert outbox_event is not None, "Outbox event was not created."

    actual_event_type = outbox_event.event_type.value if hasattr(outbox_event.event_type, "value") else str(
        outbox_event.event_type)
    actual_status = outbox_event.status.value if hasattr(outbox_event.status, "value") else str(outbox_event.status)

    assert actual_event_type.strip() == "agent_runtime.events.agent.finished", f"Unexpected event_type: '{actual_event_type}'"
    assert actual_status in ("PENDING", "PUBLISHED"), f"Unexpected outbox status: '{actual_status}'"

    logger.info("Assertion Passed: Full vertical slice verified end-to-end.")


def test_vertical_slice_duplicate_event_handling(db: Session, task_event_data: dict):
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]
    event_id = task_event_data["event_id"]

    logger.info("Executing Test 2: Simulating duplicate event retry...", event_id=str(event_id))

    mock_llm_response = LLMResponse(
        content="Task processed successfully via ReAct loop.",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("apps.agent_runtime.application.event_handlers.OpenAILLMClient") as mock_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.generate.return_value = mock_llm_response
        mock_client_cls.return_value = mock_client_instance

        # Initial Run
        first_pass = handle_task_ready_event(db=db, payload=payload, metadata=metadata, api_key="mock-key")
        assert first_pass is True

        # Duplicate Retry
        duplicate_pass = handle_task_ready_event(db=db, payload=payload, metadata=metadata, api_key="mock-key")
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


@pytest.fixture
def mock_context():
    return AgentContext(
        run_id=uuid4(),
        agent_id=uuid4(),
        task_id=uuid4(),
        workflow_instance_id=uuid4(),
        input_data={"data": {"user_id": 42, "email": "test@cortexops.ai"}, "select_keys": ["user_id"]},
        configuration={},
    )


@pytest.mark.asyncio
async def test_react_agent_single_turn_completion(mock_context):
    """Test agent completing execution without requesting tool calls."""
    mock_llm = AsyncMock(spec=BaseLLMClient)
    mock_llm.generate.return_value = LLMResponse(
        content="Task processed successfully.",
        tool_calls=[],
        finish_reason="stop",
    )

    agent = ReActLLMAgent(llm_client=mock_llm, max_iterations=3)
    result = await agent.execute_async(mock_context)

    assert result.status == AgentExecutionStatus.COMPLETED
    assert result.output_data["answer"] == "Task processed successfully."
    assert result.output_data["iterations"] == 1
    assert mock_llm.generate.call_count == 1


@pytest.mark.asyncio
async def test_react_agent_tool_invocation_loop(mock_context):
    """Test agent requesting a tool call, receiving output, and finalizing answer."""
    mock_llm = AsyncMock(spec=BaseLLMClient)

    # Turn 1: LLM requests tool execution
    # Turn 2: LLM processes tool response and returns final string
    mock_llm.generate.side_effect = [
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_123",
                    tool_name="json_transformer",
                    arguments={
                        "data": {"user_id": 42, "email": "test@cortexops.ai"},
                        "select_keys": ["user_id"],
                    },
                )
            ],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            content="Transformation complete: {'user_id': 42}",
            tool_calls=[],
            finish_reason="stop",
        ),
    ]

    agent = ReActLLMAgent(llm_client=mock_llm, max_iterations=5)
    result = await agent.execute_async(mock_context)

    assert result.status == AgentExecutionStatus.COMPLETED
    assert "user_id" in result.output_data["answer"]
    assert result.output_data["iterations"] == 2
    assert mock_llm.generate.call_count == 2


@pytest.mark.asyncio
async def test_react_agent_max_iterations_exceeded(mock_context):
    """Test agent gracefully failing when max iterations are reached."""
    mock_llm = AsyncMock(spec=BaseLLMClient)
    mock_llm.generate.return_value = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_loop",
                tool_name="json_transformer",
                arguments={"data": {}},
            )
        ],
        finish_reason="tool_calls",
    )

    agent = ReActLLMAgent(llm_client=mock_llm, max_iterations=2)
    result = await agent.execute_async(mock_context)

    assert result.status == AgentExecutionStatus.FAILED
    assert result.error.code == "MAX_ITERATIONS_EXCEEDED"
    assert mock_llm.generate.call_count == 2