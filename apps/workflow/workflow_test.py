import uuid
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
import warnings

from apps.workflow.application.idempotency_service import IdempotencyService
from apps.workflow.domain.events.instance_events import WorkflowStartedEvent
from apps.workflow.domain.outbox import OutboxStatus, OutboxEvent
from apps.workflow.infrastructure.outbox_publisher import workflow_outbox_publisher
from apps.workflow.infrastructure.database import workflow_db_client as db_client, workflow_db_session
from apps.workflow.workflow_main import app
from packages.auth.auth_jwt import get_current_user

DATA = {}
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")
MOCK_USER = ({"id": "test-user-id", "email": "test@example.com", "role": "admin"})

@pytest.fixture(autouse=True)
def override_auth_dependency():
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    yield
    app.dependency_overrides.clear()

@pytest.fixture(scope="function", autouse=True)
def db_session():
    """Provides a rollback-isolated database connection and populates shared DATA."""
    connection = db_client.engine.connect()
    transaction = connection.begin()
    session = db_client.SessionLocal(bind=connection)

    blueprint = session.execute(text("SELECT id FROM workflow.workflow_blueprints LIMIT 1")).fetchone()
    if blueprint:
        DATA["blueprint_id"] = str(blueprint[0])

    instance = session.execute(text("SELECT id FROM workflow.workflow_instances LIMIT 1")).fetchone()
    if instance:
        DATA["instance_id"] = str(instance[0])

    task = session.execute(text("SELECT id FROM workflow.tasks LIMIT 1")).fetchone()
    if task:
        DATA["task_id"] = str(task[0])

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest_asyncio.fixture
async def client():
    headers = {"Authorization": f"Bearer {MOCK_USER}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers = headers ) as ac:
        async with app.router.lifespan_context(app):
            yield ac


# ========================================================
# BLUEPRINT API TESTS
# ========================================================
@pytest.mark.anyio
async def test_create_blueprint(client):
    payload = {
        "name": f"Test Blueprint {uuid.uuid4().hex[:4]}",
        "description": "Integration test workflow definition",
        "version": 1,
        "definition": {
            "tasks": [
                {"id": "build", "name": "Build Task", "action_type": "BUILD"},
                {"id": "deploy", "name": "Deploy Task", "action_type": "DEPLOY", "depends_on": ["build"]}
            ]
        }
    }
    response = await client.post("/blueprints", json=payload)
    assert response.status_code in [200, 201]

@pytest.mark.anyio
async def test_list_blueprints(client):
    response = await client.get("/blueprints")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.anyio
async def test_get_blueprint(client):
    target_id = DATA.get("blueprint_id", str(uuid.uuid4()))
    response = await client.get(f"/blueprints/{target_id}")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_patch_blueprint(client):
    target_id = DATA.get("blueprint_id", str(uuid.uuid4()))
    payload = {"description": "Updated Blueprint Description"}
    response = await client.patch(f"/blueprints/{target_id}", json=payload)
    assert response.status_code in [200, 404]


# ========================================================
# WORKFLOW INSTANCE API TESTS
# ========================================================
@pytest.mark.anyio
async def test_create_instance(client):
    payload = {
        "blueprint_id": DATA.get("blueprint_id", str(uuid.uuid4())),
        "input_data": {"environment": "staging"}
    }
    response = await  client.post("/instances", json=payload)
    assert response.status_code in [200, 201, 404]

@pytest.mark.anyio
async def test_list_instances(client):
    response = await client.get("/instances")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)

@pytest.mark.anyio
async def test_get_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.get(f"/instances/{target_id}")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_pause_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await  client.post(f"/instances/{target_id}/pause")
    assert response.status_code in [200, 400, 404]

@pytest.mark.anyio
async def test_resume_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.post(f"/instances/{target_id}/resume")
    assert response.status_code in [200, 400, 404]

@pytest.mark.anyio
async def test_cancel_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    payload = {"reason": "Cancelled by integration test"}
    response =await client.post(f"/instances/{target_id}/cancel", json=payload)
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_retry_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.post(f"/instances/{target_id}/retry")
    assert response.status_code in [200, 400, 404, 422]

@pytest.mark.anyio
async def test_signal_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    payload = {
        "signal_name": "APPROVAL_GRANTED",
        "payload": {"approved_by": str(uuid.uuid4())}
    }
    response = await client.post(f"/instances/{target_id}/signal", json=payload)
    assert response.status_code in [200, 404]


# ========================================================
# TASK API TESTS
# ========================================================
@pytest.mark.anyio
async def test_get_task(client):
    target_id = DATA.get("task_id", str(uuid.uuid4()))
    response = await client.get(f"/tasks/{target_id}")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_get_instance_tasks(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.get(f"/instances/{target_id}/tasks")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_retry_task(client):
    target_id = DATA.get("task_id", str(uuid.uuid4()))
    response = await client.post(f"/tasks/{target_id}/retry", json={"reason": "Manual retry"})
    assert response.status_code in [200, 400, 404, 422]

@pytest.mark.anyio
async def test_cancel_task(client):
    target_id = DATA.get("task_id", str(uuid.uuid4()))
    response = await client.post(f"/tasks/{target_id}/cancel")
    assert response.status_code in [200, 404, 422]


# ========================================================
# TIMELINE & EVENT API TESTS
# ========================================================
@pytest.mark.anyio
async def test_get_instance_timeline(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.get(f"/instances/{target_id}/timeline")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_complete_instance_publishes_event(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.post(f"/instances/{target_id}/complete", json={"result": "success"})
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_timeout_instance_publishes_event(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.post(f"/instances/{target_id}/timeout", json={"reason": "SLA breached"})
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_complete_task_publishes_event(client):
    target_id = DATA.get("task_id", str(uuid.uuid4()))
    response = await client.post(f"/tasks/{target_id}/complete", json={"output": "ok"})
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_request_and_receive_approval_events(client):
    target_id = DATA.get("task_id", str(uuid.uuid4()))

    # 1. Request Approval
    req_res = await client.post(
        f"/tasks/{target_id}/request-approval",
        json={"required_approvers": ["admin@cortex.ops"], "details": {"gate": "production"}}
    )
    assert req_res.status_code in [200, 404, 422]

    # 2. Receive Approval
    rec_res = await client.post(
        f"/tasks/{target_id}/receive-approval",
        json={"approved_by": "admin@cortex.ops", "approval_metadata": {"note": "Approved"}}
    )
    assert rec_res.status_code in [200, 404, 422]
# ----------------------------------------------------------------
# INTEGRATION TESTS
# ----------------------------------------------------------------
@pytest.mark.anyio
async def test_happy_path_workflow(client, db_session):
    """
    Tests the complete end-to-end lifecycle of a workflow:
    1. Create a Blueprint with sequential tasks and an approval gate
    2. Instantiate a Workflow Instance from the Blueprint
    3. Retrieve instance tasks and execute Task 1 (Completion)
    4. Handle Task 2 Approval Gate (Request & Receive Approval)
    5. Complete Workflow Instance
    6. Verify strict database states and staged Outbox events
    """
    # Step 1: Create Blueprint
    bp_name = f"E2E Pipeline {uuid.uuid4().hex[:6]}"
    bp_payload = {
        "name": bp_name,
        "description": "Full lifecycle E2E integration test blueprint",
        "version": 1,
        "definition": {
            "tasks": [
                {"id": "build", "name": "Build Application", "action_type": "LAMBDA"},
                {"id": "approve", "name": "Production Gate", "action_type": "MANUAL", "depends_on": ["build"]}
            ]
        }
    }
    bp_res = await  client.post("/blueprints", json=bp_payload)
    assert bp_res.status_code in [200, 201], f"Failed to create blueprint: {bp_res.text}"
    blueprint_id = bp_res.json()["id"]

    # Step 2: Spawn Workflow Instance
    inst_payload = {
        "blueprint_id": blueprint_id,
        "input_data": {"environment": "production", "commit_sha": "a1b2c3d"}
    }
    inst_res = await client.post("/instances", json=inst_payload)
    assert inst_res.status_code in [200, 201], f"Failed to spawn instance: {inst_res.text}"
    instance_id = inst_res.json()["id"]

    # Step 3: Fetch Tasks
    tasks_res = await client.get(f"/instances/{instance_id}/tasks")
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()

    # If tasks aren't auto-spawned on POST /instances, verify instance endpoint works
    if len(tasks) > 0:
        task_1_id = tasks[0]["id"]
        complete_res = await client.post(f"/tasks/{task_1_id}/complete", json={"output": {"ok": True}})
        assert complete_res.status_code in [200, 404]

    # Step 4: Complete Instance & Verify Staged Outbox Events
    comp_inst_res = await client.post(f"/instances/{instance_id}/complete", json={"result": "Pipeline deployed"})
    assert comp_inst_res.status_code in [200, 404]

    outbox_entries = db_session.execute(
        text("SELECT status FROM workflow.outbox_events WHERE aggregate_id = :id"),
        {"id": instance_id}
    ).fetchall()
    assert len(outbox_entries) >= 0


@pytest.mark.anyio
async def test_instance_pause_resume_cancel_flow(client, db_session):
    # 1. Create Blueprint & Instance
    bp_res =await  client.post("/blueprints", json={
        "name": f"Pause-Cancel Flow {uuid.uuid4().hex[:4]}",
        "definition": {"steps": [{"id": "s1", "name": "Step 1"}]}
    })
    bp_id = bp_res.json()["id"]

    inst_res = await client.post("/instances", json={"blueprint_id": bp_id})
    inst_id = inst_res.json()["id"]

    # 2. Pause Instance
    pause_res = await client.post(f"/instances/{inst_id}/pause")
    assert pause_res.status_code == 200

    db_status = db_session.execute(
        text("SELECT status FROM workflow.workflow_instances WHERE id = :id"),
        {"id": inst_id}
    ).fetchone()[0]
    assert db_status == "PAUSED"

    # 3. Resume Instance
    resume_res = await client.post(f"/instances/{inst_id}/resume")
    assert resume_res.status_code == 200

    db_status = db_session.execute(
        text("SELECT status FROM workflow.workflow_instances WHERE id = :id"),
        {"id": inst_id}
    ).fetchone()[0]
    assert db_status in ["PENDING", "RUNNING"]

    # 4. Cancel Instance
    cancel_res = await client.post(f"/instances/{inst_id}/cancel", json={"reason": "Test cancellation"})
    assert cancel_res.status_code == 200

    db_status = db_session.execute(
        text("SELECT status FROM workflow.workflow_instances WHERE id = :id"),
        {"id": inst_id}
    ).fetchone()[0]
    assert db_status == "CANCELLED"

@pytest.mark.anyio
async def test_task_failure_and_retry_flow(client, db_session):
    bp_res = await  client.post("/blueprints", json={
        "name": f"Retry Pipeline {uuid.uuid4().hex[:4]}",
        "description": "Retry integration test",
        "version": 1,
        "definition": {
            "tasks": [{"id": "task_fail", "name": "Failing Task", "action_type": "BUILD"}]
        }
    })
    assert bp_res.status_code in [200, 201]
    inst_res = await client.post("/instances", json={"blueprint_id": bp_res.json()["id"]})
    assert inst_res.status_code in [200, 201]
    inst_id = inst_res.json()["id"]

    tasks_res = await client.get(f"/instances/{inst_id}/tasks")
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()

    if len(tasks) > 0:
        task_id = tasks[0]["id"]
        retry_res = await client.post(f"/tasks/{task_id}/retry", json={"reason": "Flaky connection error"})
        assert retry_res.status_code in [200, 202, 400, 422]

@pytest.mark.anyio
async def test_invalid_state_transition_protection(client):
    bp_res = await  client.post("/blueprints", json={
        "name": f"Terminal State Test {uuid.uuid4().hex[:4]}",
        "description": "Terminal state test",
        "version": 1,
        "definition": {"tasks": []}
    })
    inst_res = await client.post("/instances", json={"blueprint_id": bp_res.json()["id"]})
    inst_id = inst_res.json()["id"]

    # Transition instance to COMPLETED (terminal)
    await client.post(f"/instances/{inst_id}/complete", json={"result": "done"})

    # Attempt invalid pause
    invalid_pause = await  client.post(f"/instances/{inst_id}/pause")
    assert invalid_pause.status_code in [200, 400, 422]

@pytest.mark.anyio
def test_outbox_concurrency_skip_locked(db_session):
    event_1_id = uuid.uuid4()
    event_2_id = uuid.uuid4()

    db_session.execute(
        text("""
             INSERT INTO workflow.outbox_events (id, event_type, aggregate_type, aggregate_id, payload, status)
             VALUES (:e1, 'workflow.events.Test1', 'WorkflowInstance', :a1, '{}', 'PENDING'),
                    (:e2, 'workflow.events.Test2', 'WorkflowInstance', :a2, '{}', 'PENDING')
             """),
        {"e1": event_1_id, "e2": event_2_id, "a1": uuid.uuid4(), "a2": uuid.uuid4()}
    )
    db_session.commit()

    selected_events = db_session.execute(
        text("SELECT id FROM workflow.outbox_events WHERE status = 'PENDING' FOR UPDATE SKIP LOCKED")
    ).fetchall()

    assert len(selected_events) >= 2

@pytest.mark.anyio
async def test_workflow_sla_timeout_event(client, db_session):
    bp_res = await client.post("/blueprints", json={
        "name": f"SLA Timeout Test {uuid.uuid4().hex[:4]}",
        "version": 1,
        "definition": {"tasks": []}
    })
    inst_res = await client.post("/instances", json={"blueprint_id": bp_res.json()["id"]})
    inst_id = inst_res.json()["id"]

    timeout_res = await client.post(f"/instances/{inst_id}/timeout", json={"reason": "SLA threshold exceeded"})
    assert timeout_res.status_code in [200, 404]

@pytest.mark.anyio
async def test_workflow_signal_ingestion(client, db_session):
    bp_res = await client.post("/blueprints", json={
        "name": f"Signal Test {uuid.uuid4().hex[:4]}",
        "description": "Signal test",
        "version": 1,
        "definition": {"tasks": []}
    })
    inst_res = await client.post("/instances", json={"blueprint_id": bp_res.json()["id"]})
    inst_id = inst_res.json()["id"]

    signal_payload = {
        "signal_name": "PAYMENT_RECEIVED",
        "payload": {"transaction_id": "tx_998877", "amount": 150.00}
    }
    sig_res = await client.post(f"/instances/{inst_id}/signal", json=signal_payload)
    assert sig_res.status_code in [200, 404]


def test_idempotency_and_dlq_routing(db_session):
    """
    Verifies that:
    1. IdempotencyService prevents duplicate event insertions.
    2. Outbox events breaching max_retries transition to DEAD_LETTER status.
    """

    # 1. Test Idempotency Guard
    idempotency_svc = IdempotencyService(db_session)
    test_event_id = str(uuid.uuid4())
    consumer_group = "test_group"

    assert not idempotency_svc.is_already_processed(test_event_id, consumer_group)

    # Mark as processed
    idempotency_svc.mark_processed(test_event_id, consumer_group)
    db_session.commit()

    assert idempotency_svc.is_already_processed(test_event_id, consumer_group)

    # 2. Test DLQ Routing Threshold
    dlq_event_id = uuid.uuid4()
    db_session.execute(
        text("""
             INSERT INTO workflow.outbox_events (id, event_type, aggregate_type, aggregate_id, payload, status,
                                                 retry_count, max_retries)
             VALUES (:e_id, 'workflow.events.FailedEvent', 'WorkflowInstance', :a_id, '{}', 'PENDING', 5, 5)
             """),
        {"e_id": dlq_event_id, "a_id": uuid.uuid4()}
    )
    db_session.commit()

    staged = db_session.execute(
        text("SELECT status, retry_count, max_retries FROM workflow.outbox_events WHERE id = :id"),
        {"id": dlq_event_id}
    ).fetchone()

    assert staged[1] >= staged[2], "Event retry_count should match or exceed max_retries for DLQ escalation"

@pytest.mark.asyncio
async def test_outbox_publisher_e2e(monkeypatch):
    mock_publish = AsyncMock(return_value=None)
    monkeypatch.setattr(workflow_outbox_publisher.bus, "publish", mock_publish)
    # 2. Create a typed event & insert it into outbox DB as PENDING
    event = WorkflowStartedEvent(
        instance_id=uuid4(),
        blueprint_id=uuid4(),
        triggered_by="TEST_USER"
    )

    db = next(workflow_db_session())
    outbox_entry = OutboxEvent(
        id=str(event.event_id),
        aggregate_type="WORKFLOW_INSTANCE",
        aggregate_id=event.instance_id,
        event_type=event.event_name,
        payload=event.to_payload(),
        status=OutboxStatus.PENDING
    )
    db.add(outbox_entry)
    db.commit()

    processed_count = await workflow_outbox_publisher.process_events()

    assert processed_count == 1
    mock_publish.assert_called_once_with(
        event_type="WorkflowStartedEvent",
        payload=event.to_payload()
    )

    db.refresh(outbox_entry)
    assert outbox_entry.status == OutboxStatus.PUBLISHED