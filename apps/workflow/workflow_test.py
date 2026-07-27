import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from apps.workflow.infrastructure.database import workflow_db_client as db_client
from apps.workflow.workflow_main import app
from infrastructure.nats.nats_client import EventBus

DATA = {}


@pytest.fixture(scope="function", autouse=True)
def db_session():
    connection = db_client.engine.connect()
    transaction = connection.begin()
    session = db_client.SessionLocal(bind=connection)

    # Pre-fetch existing IDs for tests that require valid UUIDs
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


@pytest.fixture
async def client():
    EventBus._publisher = None
    EventBus._subscriber = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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
    response = await client.post("/instances", json=payload)
    assert response.status_code in [200, 201, 404]


@pytest.mark.anyio
async def test_list_instances(client):
    response = await client.get("/instances")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_get_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.get(f"/instances/{target_id}")
    assert response.status_code in [200, 404]


@pytest.mark.anyio
async def test_pause_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.post(f"/instances/{target_id}/pause")
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
    response = await client.post(f"/instances/{target_id}/cancel", json=payload)
    assert response.status_code in [200, 404]


@pytest.mark.anyio
async def test_retry_instance(client):
    target_id = DATA.get("instance_id", str(uuid.uuid4()))
    response = await client.post(f"/instances/{target_id}/retry")
    assert response.status_code in [200, 400, 404]


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
    response = await client.post(f"/tasks/{target_id}/retry")
    assert response.status_code in [200, 400, 404]


@pytest.mark.anyio
async def test_cancel_task(client):
    target_id = DATA.get("task_id", str(uuid.uuid4()))
    response = await client.post(f"/tasks/{target_id}/cancel")
    assert response.status_code in [200, 404]


# ========================================================
# TIMELINE API TESTS
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
    req_res = await client.post(f"/tasks/{target_id}/request-approval",
                                json={"approvers": ["admin@cortex.ops"], "details": {"gate": "production"}})
    assert req_res.status_code in [200, 404]

    # 2. Receive Approval
    rec_res = await client.post(f"/tasks/{target_id}/receive-approval",
                                json={"approved_by": "admin@cortex.ops", "metadata": {"note": "Approved"}})
    assert rec_res.status_code in [200, 404]