import socket
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
import pytest_asyncio
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.agent_runtime.application.event_handlers import handle_task_ready_event
from apps.agent_runtime.domain.agent_contract import AgentContext, AgentExecutionStatus
from apps.agent_runtime.domain.agents import Agent, AgentStatus
from apps.agent_runtime.infrastructure.database import agent_runtime_db_client as db_client, agent_db_session
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.llm.base_client import BaseLLMClient, LLMResponse, ToolCall
from apps.agent_runtime.llm.llm_agent import ReActLLMAgent
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository
from apps.agent_runtime.repository.outbox_repository import OutboxRepository
from apps.agent_runtime.repository.processed_events_repository import ProcessedEventsRepository
from apps.agent_runtime.tools.tool_registry import ToolRegistryError, global_tool_registry, ToolRegistry
from packages.events.context import RequestContext
from packages.telemetry.scrubber import sanitize_telemetry_dict, REDACTED_STRING

DATA = {}
memory_exporter = InMemorySpanExporter()
provider = trace.get_tracer_provider()
if not isinstance(provider, TracerProvider):
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

# Attach SimpleSpanProcessor so spans flush immediately into memory_exporter
provider.add_span_processor(SimpleSpanProcessor(memory_exporter))

@pytest.fixture(scope="session", autouse=True)
def setup_test_agent():
    """Seeds a single test agent once for the test module and commits it to the DB.
    Ensures all event handlers and separate DB sessions can query it.
    """
    connection = db_client.engine.connect()
    session = db_client.SessionLocal(bind=connection)

    # 1. Check if an active agent already exists
    agent = session.execute(
        text("SELECT id, slug FROM agent_runtime.agents WHERE status = 'ACTIVE' LIMIT 1")
    ).fetchone()

    if agent:
        DATA["agent_id"] = agent[0]
        DATA["agent_slug"] = agent[1]
        DATA["created_by_test"] = False
    else:
        # 2. Explicitly seed test agent and COMMIT so all concurrent DB connections see it
        test_agent_id = uuid4()
        test_slug = "test-agent-slug"

        session.execute(
            text(
                """
                INSERT INTO agent_runtime.agents (id, name, slug, status)
                VALUES (:id, :name, :slug, :status)
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": test_agent_id,
                "name": "Test Integration Agent",
                "slug": test_slug,
                "status": "ACTIVE",
            },
        )
        session.commit()

        DATA["agent_id"] = test_agent_id
        DATA["agent_slug"] = test_slug
        DATA["created_by_test"] = True

    session.close()
    connection.close()


@pytest.fixture(scope="function")
def db():
    """Provides a fresh DB session per test function."""
    connection = db_client.engine.connect()
    session = db_client.SessionLocal(bind=connection)
    yield session
    session.close()
    connection.close()


@pytest.fixture
def task_event_data():
    """Generates task payload matching the seeded DB agent."""
    event_id = uuid4()
    task_id = uuid4()
    workflow_instance_id = uuid4()

    payload = {
        "event_id": str(event_id),
        "task_id": str(task_id),
        "workflow_instance_id": str(workflow_instance_id),
        "agent_id": str(DATA["agent_id"]),
        "agent_slug": DATA["agent_slug"],
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
        "agent_id": DATA["agent_id"],
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

        success = handle_task_ready_event(
            db=db,
            payload=payload,
            metadata=metadata,
            api_key="mock-key"
        )
        assert success is True, "Event processing returned False instead of True"

    run_repo = AgentRunsRepository(db)
    outbox_repo = OutboxRepository(db)
    processed_repo = ProcessedEventsRepository(db)

    # 1. Verify AgentRun Record State
    run = run_repo.get_by_task_id(task_id)
    assert run is not None, "AgentRun record was not created in the database."

    run_status_str = run.status.value if hasattr(run.status, "value") else str(run.status)
    assert run_status_str == "COMPLETED", f"Expected COMPLETED status, got '{run.status}'."
    assert "answer" in run.output_data
    assert run.output_data["answer"] == "Task processed successfully via ReAct loop."

    # 2. Verify Idempotency Record
    is_processed = processed_repo.is_processed(
        event_id=event_id,
        consumer_group="agent-runtime-task-consumer"
    )
    assert is_processed is True, "Event was not recorded in processed_events table."

    # 3. Verify Outbox Staging
    outbox_event = outbox_repo.get_latest_by_aggregate(run.id)
    assert outbox_event is not None, "Outbox event was not created."


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


@pytest.fixture
def registry():
    return ToolRegistry()


def test_default_tools_and_schemas_registered(registry):
    schemas = registry.get_all_schemas()
    registered_names = [s["name"] for s in schemas]

    assert "json_transformer" in registered_names
    assert "task_reader" in registered_names
    assert len(schemas) == 2


def test_json_transformer_tool_execution(registry):
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


def test_task_reader_tool_validation_failure(registry):
    invalid_input = {
        "payload": {"action": "deploy"},
        "required_fields": ["action", "target_env"],
    }

    result = registry.execute_tool(
        tool_name="task_reader",
        parameters=invalid_input,
    )

    assert result.success is False
    assert result.result is None
    assert "Missing required fields" in result.error


def test_unregistered_tool_resolution_raises_error(registry):
    with pytest.raises(ToolRegistryError) as exc_info:
        registry.resolve("non_existent_tool")

    assert "Tool 'non_existent_tool' is not registered" in str(exc_info.value)


def test_global_tool_registry_instance():
    tool = global_tool_registry.get("json_transformer")
    assert tool is not None
    assert tool.name == "json_transformer"


@pytest.fixture
def mock_context():
    return AgentContext(
        run_id=uuid4(),
        agent_id=DATA.get("agent_id", uuid4()),
        task_id=uuid4(),
        workflow_instance_id=uuid4(),
        input_data={"data": {"user_id": 42, "email": "test@cortexops.ai"}, "select_keys": ["user_id"]},
        configuration={},
    )


@pytest.mark.asyncio
async def test_react_agent_single_turn_completion(mock_context):
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


@pytest.mark.asyncio
async def test_react_agent_tool_invocation_loop(mock_context):
    mock_llm = AsyncMock(spec=BaseLLMClient)

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


@pytest.mark.asyncio
async def test_react_agent_max_iterations_exceeded(mock_context):
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


# ==============================================================================
# TEST : OPENTELEMETRY Functionality
# ==============================================================================

def test_telemetry_run(db: Session, task_event_data: dict):
    memory_exporter.clear()

    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]
    event_id = task_event_data["event_id"]
    task_id = task_event_data["task_id"]

    mock_llm_response = LLMResponse(
        content="Task processed successfully via ReAct loop.",
        tool_calls=[],
        finish_reason="stop",
    )

    RequestContext.set(
        correlation_id=f"corr-{event_id}",
        tenant_id="tenant-cortexops",
        causation_id=str(event_id)
    )

    with patch("apps.agent_runtime.application.event_handlers.OpenAILLMClient") as mock_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.generate.return_value = mock_llm_response
        mock_client_cls.return_value = mock_client_instance

        success = handle_task_ready_event(
            db=db,
            payload=payload,
            metadata=metadata,
            api_key="mock-key"
        )
        assert success is True

    spans = memory_exporter.get_finished_spans()
    assert len(spans) > 0, "No OpenTelemetry spans were recorded during execution!"

    span_names = [span.name for span in spans]
    assert any("handle_task_ready_event" in name or "agent_run" in name for name in span_names)

    RequestContext.clear()


def test_telemetry_run_duplicate(db: Session, task_event_data: dict):

    memory_exporter.clear()
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]

    mock_llm_response = LLMResponse(
        content="Task processed successfully via ReAct loop.",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("apps.agent_runtime.application.event_handlers.OpenAILLMClient") as mock_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.generate.return_value = mock_llm_response
        mock_client_cls.return_value = mock_client_instance

        first_pass = handle_task_ready_event(db=db, payload=payload, metadata=metadata, api_key="mock-key")
        assert first_pass is True

        spans_pass_1 = len(memory_exporter.get_finished_spans())
        memory_exporter.clear()

        second_pass = handle_task_ready_event(db=db, payload=payload, metadata=metadata, api_key="mock-key")
        assert second_pass is True

        spans_pass_2 = memory_exporter.get_finished_spans()

        assert len(spans_pass_2) < spans_pass_1

# ==============================================================================
# TEST : TOOL EXECUTION FAILURES
# ==============================================================================
def test_tool_validation_failure(registry: ToolRegistry):
    tracer = trace.get_tracer("agent-runtime-tools")

    invalid_input = {
        "payload": {"action": "deploy"},
        "required_fields": ["action", "target_env"],
    }

    with tracer.start_as_current_span("tool.execution.test") as span:
        result = registry.execute_tool(
            tool_name="task_reader",
            parameters=invalid_input,
        )

        assert result.success is False
        assert result.result is None
        assert "Missing required fields" in result.error

        if span.is_recording():
            span.set_status(StatusCode.ERROR, description=result.error)
            span.set_attribute("tool.name", "task_reader")
            span.set_attribute("tool.success", False)


@pytest.mark.asyncio
async def test_react_loop_tool_failure_handling(mock_context: AgentContext):
    mock_llm = AsyncMock(spec=BaseLLMClient)

    mock_llm.generate.return_value = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_fail_001",
                tool_name="non_existent_tool",
                arguments={"data": {}},
            )
        ],
        finish_reason="tool_calls",
    )

    agent = ReActLLMAgent(llm_client=mock_llm, max_iterations=2)

    with patch("apps.agent_runtime.llm.llm_agent.logger") as mock_logger:
        result = await agent.execute_async(mock_context)

        assert result.status == AgentExecutionStatus.FAILED
        assert result.error is not None

        mock_logger.error.assert_called()


# ==============================================================================
# TEST : NATS & EVENT PROCESSING FAILURES
# ==============================================================================
def test_nats_handler_database_exception(db: Session, task_event_data: dict):
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]

    RequestContext.set(
        correlation_id="test-nats-failure-corr",
        tenant_id="tenant-cortexops",
    )

    with patch.object(db, "commit", side_effect=Exception("Database Connection Timeout")):
        with patch("apps.agent_runtime.application.event_handlers.OpenAILLMClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.generate.return_value = LLMResponse(
                content="Task completed", tool_calls=[], finish_reason="stop"
            )
            mock_client_cls.return_value = mock_client_instance

            success = handle_task_ready_event(
                db=db,
                payload=payload,
                metadata=metadata,
                api_key="mock-key"
            )

            assert success is False

    RequestContext.clear()

# ==============================================================================
# TEST : OTEL COLLECTOR PROCESSING
# ==============================================================================
def test_collector_outage_isolation(db: Session, task_event_data: dict):
    """Phase 16 - Test 5: Verifies that if the OTel Collector endpoint is completely unreachable,
    the Agent Runtime continues to process business events without throwing exceptions or hanging.
    """
    payload = task_event_data["payload"]
    metadata = task_event_data["metadata"]
    event_id = task_event_data["event_id"]

    RequestContext.set(
        correlation_id=f"collector-down-{event_id}",
        tenant_id="tenant-cortexops",
    )

    mock_llm_response = LLMResponse(
        content="Task processed cleanly despite collector outage.",
        tool_calls=[],
        finish_reason="stop",
    )

    # 1. Force the OTLP Exporter to attempt export to a closed socket port (Unreachable Collector)
    unreachable_exporter = OTLPSpanExporter(
        endpoint="http://127.0.0.1:59999", # Unused local port causing active socket errors
        insecure=True,
        timeout=1, # Strict 1s timeout to ensure non-blocking backoff
    )

    with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter.export",
                side_effect=socket.error("Connection refused")):
        with patch("apps.agent_runtime.application.event_handlers.OpenAILLMClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.generate.return_value = mock_llm_response
            mock_client_cls.return_value = mock_client_instance

            # 2. Execute vertical slice handler under active OTel failure
            success = handle_task_ready_event(
                db=db,
                payload=payload,
                metadata=metadata,
                api_key="mock-key"
            )

            assert success is True, "Agent Runtime failed when the OTel Collector went down!"

    RequestContext.clear()

# ==============================================================================
# TEST : REDACT Test for Observability Security
# ==============================================================================

def test_sensitive_data_redaction():
    """Phase 17 - Test 12: Verifies sensitive keys and tokens are fully scrubbed."""
    raw_payload = {
        "user_id": "usr-12345",
        "api_key": "sk-proj-99999999999999999999",
        "nested": {
            "password": "SuperSecretPassword123!",
            "normal_field": "safe_value"
        },
        "headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        }
    }

    sanitized = sanitize_telemetry_dict(raw_payload)

    assert sanitized["user_id"] == "usr-12345"
    assert sanitized["api_key"] == REDACTED_STRING
    assert sanitized["nested"]["password"] == REDACTED_STRING
    assert sanitized["nested"]["normal_field"] == "safe_value"
    assert sanitized["headers"]["Authorization"] == REDACTED_STRING

# ==============================================================================
# TEST : DELETING TEST AGENT FROM DB
# ==============================================================================

def test_delete_test_agent(db: Session):
    """Executes last to cleanly delete all generated test runs and the seeded test agent."""
    if DATA.get("created_by_test") and DATA.get("agent_id"):
        test_agent_id = DATA["agent_id"]

        db.execute(
            text("DELETE FROM agent_runtime.agent_runs WHERE agent_id = :agent_id"),
            {"agent_id": test_agent_id},
        )
        # Delete the test agent record
        db.execute(
            text("DELETE FROM agent_runtime.agents WHERE id = :agent_id"),
            {"agent_id": test_agent_id},
        )
        db.commit()

        # Verify deletion
        res = db.execute(
            text("SELECT id FROM agent_runtime.agents WHERE id = :agent_id"),
            {"agent_id": test_agent_id},
        ).fetchone()

        assert res is None, "Test agent was not securely deleted from the database."
