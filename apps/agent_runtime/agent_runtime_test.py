"""
import sys
import traceback
from uuid import uuid4

from apps.agent_runtime.application.event_handlers import handle_task_ready_event
from apps.agent_runtime.infrastructure.database import agent_db_session
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository
from apps.agent_runtime.repository.outbox_repository import OutboxRepository
from apps.agent_runtime.repository.processed_events_repository import ProcessedEventsRepository


def run_vertical_slice_test():
    logger.info("Initiating Vertical Slice Test ......")

    # Generating the random identifiers
    event_id = uuid4()
    task_id = uuid4()
    workflow_instance_id = uuid4()
    agent_slug = "test-agent-1"

    test_payload = {
        "event_id": str(event_id),
        "task_id": str(task_id),
        "workflow_instance_id": str(workflow_instance_id),
        "agent_slug": agent_slug,
        "input_data": {
            "action_type": "execute",
            "input_reference": str(uuid4()),
            "payload": {"test_key": "test_value"}
        }
    }

    test_metadata = {
        "event_id": str(event_id),
        "event_type": "workflow.events.task.ready"
    }
    # Obtain Database Session from generator
    db_gen = agent_db_session()
    db = next(db_gen)

    try:
        #### TEST 1: Process Event for the First Time
        logger.info("Executing Test 1: Processing new task event ...", event_id= str(event_id))
        success = handle_task_ready_event(db=db, payload=test_payload, metadata=test_metadata)
        assert success is True, "Event Processing Failed."

        # Verify DB Assertions
        run_repo = AgentRunsRepository(db)
        outbox_repo = OutboxRepository(db)
        processed_repo = ProcessedEventsRepository(db)
        logger.info("Verified DB Assertions")

        # Asserting Agent Run record Created and Completed
        run = run_repo.get_by_task_id(task_id)
        assert run is not None, "AgentRun record was not created"
        run_status_str = run.status.value if hasattr(run.status, "value") else str(run.status)
        assert run_status_str == "COMPLETED", f"Expected status COMPLETED, got instead '{run.status}'."
        assert run.output_data.get("message") == "TestAgent executed successfully"
        logger.info("Assertion Passed: AgentRun created with COMPLETED status.", run_id = str(run.id))

        # Assert Event Mark Processed
        is_processed = processed_repo.is_processed(event_id= event_id, consumer_group="agent-runtime-task-consumer")
        assert is_processed is True, "Event was not marked as processed in DB."
        logger.info("Assertion Passed: ProcessedEvent Record Verified")

        # Assert Outbox Event Created
        outbox_event = outbox_repo.get_latest_by_aggregate(run.id)
        assert outbox_event is not None, "Outbox event was not generated."
        assert outbox_event.event_type == "agent_runtime.events.agent.finished"
        assert outbox_event.status == "PENDING"
        logger.info("Assertion Passed: OutboxEvent verified.", outbox_id=str(outbox_event.id))
        logger.info("Assertion Passed: Event pipeline executed successfully.")

        #### Test 2: Duplicate Event Handling
        logger.info("Executing Test 2: Simulating duplicate event retry ... ", event_id= str(event_id))
        duplicate_success = handle_task_ready_event(db=db, payload = test_payload, metadata=test_metadata)
        assert duplicate_success is True, "Duplicate Event - Event Handling Failed"
        logger.info("Assertion Passed: Duplicate Event safely ignored.")
        logger.info("Vertical Slice Test -> PASSED")

    except Exception as e:
        logger.error("Vertical Slice Test -> FAILED", error = str(e))
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_gen.close()

if __name__ == "__main__":
    run_vertical_slice_test()
"""
from uuid import uuid4
import pytest
from sqlalchemy.orm import Session

from apps.agent_runtime.application.event_handlers import handle_task_ready_event
from apps.agent_runtime.infrastructure.database import agent_db_session
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.agent_run_repository import AgentRunsRepository
from apps.agent_runtime.repository.outbox_repository import OutboxRepository
from apps.agent_runtime.repository.processed_events_repository import ProcessedEventsRepository


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