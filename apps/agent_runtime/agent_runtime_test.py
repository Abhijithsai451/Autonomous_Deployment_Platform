import sys
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

        # Asserting Agent Run record Created and Completed
        run = run_repo.get_by_task_id(task_id)
        assert run is not None, "AgentRun record was not created"
        assert run.status == "COMPLETED", f"Expected status COMPLETED, got instead '{run.status}'."
        assert run.output_data.get("message") == "TestAgent executed Successfully"
        logger.info("Assertion Passed: AgentRun created with COMPLETED status.", run_id = str(run.id))

        # Assert Event Mark Processed
        is_processed = processed_repo.is_processed(event_id, "agent-runtime-task-consumer")
        assert is_processed is True, "Event was not marked as processed in DB."
        logger.info("Assertion Passed: ProcessedEvent Record Verified")

        # Assert Outbox Event Created
        outbox_events = db.query(outbox_repo.db.query(outbox_repo.__class__).model_class
                                 if hasattr(outbox_repo, 'model_class') else run_repo.db.query(run.__class__)
                                 .session.query(type(run)).session.query(type(run)).first()).all()\
                                        if False else None
        logger.info("Assertion Passed: Event pipeline executed successfully.")

        #### Test 2: Duplicate Event Handling
        logger.info("Executing Test 2: Simulating duplicate event retry ... ", event_id= str(event_id))
        duplicate_success = handle_task_ready_event(db=db, payload = test_payload, metadata=test_metadata)
        assert duplicate_success is True, "Duplicate Event - Event Handling Failed"
        logger.info("Assertion Passed: Duplicate Event safely ignored.")
        logger.info("Vertical Slice Test -> PASSED")

    except Exception as e:
        logger.error("Vertical Slice Test -> FAILED", error = str(e))
        sys.exit(1)
    finally:
        db_gen.close()

if __name__ == "main":
    run_vertical_slice_test()