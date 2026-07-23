import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from apps.organization.infrastructure.database import org_db_client as db_client
from apps.organization.org_main import app
from infrastructure.nats.nats_client import EventBus

DATA = {}
@pytest.fixture(scope="function", autouse=True)
def db_session():
    connection = db_client.engine.connect()
    transaction = connection.begin()
    session = db_client.SessionLocal(bind=connection)

    # Pre-fetch existing IDs for tests that require valid UUIDs
    org = session.execute(text("SELECT id FROM organization.organizations LIMIT 1")).fetchone()
    if org: DATA["org_id"] = str(org[0])

    project = session.execute(text("SELECT id FROM organization.projects LIMIT 1")).fetchone()
    if project: DATA["project_id"] = str(project[0])

    dept = session.execute(text("SELECT id FROM organization.departments LIMIT 1")).fetchone()
    if dept: DATA["dept_id"] = str(dept[0])

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
# ORGANIZATION API TESTS
# ========================================================

@pytest.mark.anyio
async def test_create_organization(client):
    payload = {
        "name": "Test Org",
        "slug": f"test-slug-{uuid.uuid4().hex[:4]}"
    }
    response = await client.post("/organizations", json=payload)
    assert response.status_code in [200, 201]

@pytest.mark.anyio
async def test_list_organizations(client):
    response = await client.get("/organizations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.anyio
async def test_get_organization(client):
    target_id = DATA.get("org_id", str(uuid.uuid4()))
    response = await client.get(f"/organizations/{target_id}")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_patch_organization(client):
    target_id = DATA.get("org_id", str(uuid.uuid4()))
    payload = {"name": "Updated Org Name"}
    response = await client.patch(f"/organizations/{target_id}", json=payload)
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_update_organization_status(client):
    target_id = DATA.get("org_id", str(uuid.uuid4()))
    payload = {"status": "ACTIVE"}
    response = await client.patch(f"/organizations/{target_id}/status", json=payload)
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_suspend_organization(client):
    target_id = DATA.get("org_id", str(uuid.uuid4()))
    response = await client.post(f"/organizations/{target_id}/suspend")
    assert response.status_code in [200, 404]

# ========================================================
# PROJECT API TESTS
# ========================================================

@pytest.mark.anyio
async def test_create_project(client):
    payload = {
        "organization_id": DATA.get("org_id", str(uuid.uuid4())),
        "name": "Test Project",
        "description": "Desc",
        "lifecycle": "ACTIVE"
    }
    response = await client.post("/projects", json=payload)
    assert response.status_code in [200, 201]

@pytest.mark.anyio
async def test_list_projects(client):
    response = await client.get("/projects")
    assert response.status_code == 200

@pytest.mark.anyio
async def test_get_project(client):
    target_id = DATA.get("project_id", str(uuid.uuid4()))
    response = await client.get(f"/projects/{target_id}")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_patch_project(client):
    target_id = DATA.get("project_id", str(uuid.uuid4()))
    payload = {"description": "New Project Description"}
    response = await client.patch(f"/projects/{target_id}", json=payload)
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_update_project_status(client):
    target_id = DATA.get("project_id", str(uuid.uuid4()))
    payload = {"status": "ARCHIVED"}
    response = await client.patch(f"/projects/{target_id}/status", json=payload)
    assert response.status_code in [200, 404]

# ========================================================
# DEPARTMENT API TESTS
# ========================================================

@pytest.mark.anyio
async def test_create_department(client):
    payload = {
        "organization_id": DATA.get("org_id", str(uuid.uuid4())),
        "name": "DevOps",
        "description": "SRE Team",
        "type": "SRE"
    }
    response = await client.post("/departments", json=payload)
    assert response.status_code in [200, 201]

@pytest.mark.anyio
async def test_list_departments(client):
    response = await client.get("/departments")
    assert response.status_code == 200

@pytest.mark.anyio
async def test_get_department(client):
    target_id = DATA.get("dept_id", str(uuid.uuid4()))
    response = await client.get(f"/departments/{target_id}")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_patch_department(client):
    target_id = DATA.get("dept_id", str(uuid.uuid4()))
    payload = {"name": "Core SRE"}
    response = await client.patch(f"/departments/{target_id}", json=payload)
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_update_department_status(client):
    target_id = DATA.get("dept_id", str(uuid.uuid4()))
    payload = {"status": "UPDATED"}
    response = await client.patch(f"/departments/{target_id}/status", json=payload)
    assert response.status_code in [200, 404]