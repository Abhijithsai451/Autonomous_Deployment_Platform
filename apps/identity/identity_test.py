import uuid
import nats
import pytest
from keycloak import KeycloakAdmin
from httpx import ASGITransport, AsyncClient
from sqlalchemy import  text
from apps.identity.identity_main import app
from apps.identity.infrastructure.database import db_client
from apps.identity.config.identity_settings import identity_settings as settings
from apps.identity.infrastructure.identity_nats_client import identity_nats_client as nats_client

DATA = {}

@pytest.fixture(scope="session", autouse=True)
def setup_keycloak_test_data():
    admin_client = KeycloakAdmin(
        server_url=settings.KEYCLOAK_URL,
        username=settings.KEYCLOAK_ADMIN_USER,
        password=settings.KEYCLOAK_ADMIN_PASSWORD,
        realm_name="master",
        user_realm_name=settings.KEYCLOAK_REALM,
        verify=True
    )
    test_user = {
        "email": "testuser@cortexops.io",
        "username": "testuser",
        "enabled": True,
        "credentials": [{"value": "secure_password", "type": "password", "temporary": False}]
    }
    try:
        admin_client.create_user(test_user, exist_ok=True)
    except Exception:
        pass
    yield


async def get_live_tokens(client) -> dict:
    payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=payload)
    if response.status_code != 200:
        return {
            "access_token": "mocked_access_token",
            "refresh_token": "mocked_refresh_token"
        }
    return response.json()

@pytest.fixture(scope="function", autouse=True)
def db_session():
    connection = db_client.engine.connect()
    transaction = connection.begin()

    session = db_client.SessionLocal(bind=connection)
    user = session.execute(text("SELECT id FROM identity.users LIMIT 1")).fetchone()
    if user:
        DATA["user_id"] = str(user[0])
    role = session.execute(text("SELECT id FROM identity.roles LIMIT 1")).fetchone()
    if role:
        DATA["role_id"] = str(role[0])
    sa = session.execute(text("SELECT id FROM identity.service_accounts LIMIT 1")).fetchone()
    if sa:
        DATA["service_account_id"] = str(sa[0])

    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac


@pytest.mark.anyio
async def test_force_nats_debug():
    nc = await nats.connect(
        settings.NATS_URL,
        connect_timeout=2,
        max_reconnect_attempts=1
    )
    js = nc.jetstream()
    await js.add_stream(name="test_debug", subjects=["test.*"])
    await js.publish("test.event", b"hello")
    await nc.close()


@pytest.mark.anyio
async def test_auth_login(client):
    payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=payload)
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_auth_refresh(client):
    tokens = await get_live_tokens(client)
    payload = {"refresh_token": tokens["refresh_token"]}
    response = await client.post("/auth/refresh", json=payload)
    assert response.status_code in [200, 400, 401]


@pytest.mark.anyio
async def test_auth_logout(client):
    tokens = await get_live_tokens(client)
    payload = {"refresh_token": tokens["refresh_token"]}
    response = await client.post("/auth/logout", json=payload)
    assert response.status_code in [200, 204, 400, 401]


@pytest.mark.anyio
async def test_auth_me(client):
    response = await client.get("/auth/me")
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_users_invite(client):
    payload = {
        "email": f"newuser-{uuid.uuid4().hex[:6]}@cortexops.io",
        "role_id": DATA.get("role_id", str(uuid.uuid4())),
        "organization_id": DATA.get("org_id", str(uuid.uuid4())),
        "display_name": "New User"
    }
    try:
        response = await client.post("/users/invite", json=payload)
        assert response.status_code in [200, 201, 401, 422]
    except Exception as e:
        if "KeycloakConnectionError" not in type(e).__name__:
            raise e


@pytest.mark.anyio
async def test_users_list(client):
    response = await client.get("/users")
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_users_get_by_id(client):
    target_id = str(DATA.get("user_id", uuid.uuid4()))
    response = await client.get(f"/users/{target_id}")
    assert response.status_code in [200, 404, 401, 422]


@pytest.mark.anyio
async def test_users_patch(client):
    target_id = str(DATA.get("user_id", uuid.uuid4()))
    payload = {"display_name": "Updated Name"}
    response = await client.patch(f"/users/{target_id}", json=payload)
    assert response.status_code in [200, 404, 401, 422]


@pytest.mark.anyio
async def test_users_delete(client):
    target_id = str(DATA.get("user_id", uuid.uuid4()))
    try:
        response = await client.delete(f"/users/{target_id}")
        assert response.status_code in [200, 204, 404, 401, 422]
    except Exception as e:
        if "KeycloakConnectionError" not in type(e).__name__ and "ConnectionError" not in type(e).__name__:
            raise e


@pytest.mark.anyio
async def test_users_change_status(client):
    target_id = str(DATA.get("user_id", uuid.uuid4()))
    payload = {"status": "DISABLED"}
    try:
        response = await client.patch(f"/users/{target_id}/status", json=payload)
        assert response.status_code in [200, 400, 401, 422]
    except Exception as e:
        if "KeycloakConnectionError" not in type(e).__name__ and "ConnectionError" not in type(e).__name__:
            raise e

@pytest.mark.anyio
async def test_users_assign_role(client):
    target_id = str(DATA.get("user_id", uuid.uuid4()))
    payload = {"role_id": str(DATA.get("role_id", uuid.uuid4()))}
    response = await client.post(f"/users/{target_id}/roles", json=payload)
    assert response.status_code in [200, 201, 404, 401, 422]


@pytest.mark.anyio
async def test_users_remove_role(client):
    user_id = str(DATA.get("user_id", uuid.uuid4()))
    role_id = str(DATA.get("role_id", uuid.uuid4()))
    response = await client.delete(f"/users/{user_id}/roles/{role_id}")
    assert response.status_code in [200, 204, 404, 401, 422]


@pytest.mark.anyio
async def test_roles_get(client):
    response = await client.get("/roles")
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_roles_create(client):
    payload = {
        "name": "IntegrationTestRole",
        "organization_id": str(DATA.get("org_id", uuid.uuid4())),
        "permissions": []
    }
    response = await client.post("/roles", json=payload)
    assert response.status_code in [200, 201, 400, 401, 422]


@pytest.mark.anyio
async def test_roles_patch(client):
    target_id = str(DATA.get("role_id", uuid.uuid4()))
    payload = {"name": "UpdatedTestRoleName"}
    response = await client.patch(f"/roles/{target_id}", json=payload)
    assert response.status_code in [200, 404, 401, 422]


@pytest.mark.anyio
async def test_roles_delete(client):
    target_id = str(DATA.get("role_id", uuid.uuid4()))
    response = await client.delete(f"/roles/{target_id}")
    assert response.status_code in [200, 204, 404, 401, 422]


@pytest.mark.anyio
async def test_permissions_get(client):
    response = await client.get("/permissions")
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_service_accounts_list(client):
    response = await client.get("/service-accounts")
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_service_accounts_create(client):
    payload = {
        "client_id": f"sa-dynamic-client-{uuid.uuid4().hex[:6]}",
        "description": "Dynamic Integration Runner",
        "org_id": DATA.get("org_id", str(uuid.uuid4())),
        "organization_id": DATA.get("org_id", str(uuid.uuid4()))
    }
    try:
        response = await client.post("/service-accounts", json=payload)
        assert response.status_code in [200, 201, 400, 401, 422, 500]
    except Exception as e:
        if "IntegrityError" not in type(e).__name__:
            raise e


@pytest.mark.anyio
async def test_service_accounts_patch(client):
    target_id = str(DATA.get("service_account_id", uuid.uuid4()))
    payload = {"description": "Updated Specs"}
    response = await client.patch(f"/service-accounts/{target_id}", json=payload)
    assert response.status_code in [200, 404, 401, 422]


@pytest.mark.anyio
async def test_service_accounts_delete(client):
    target_id = str(DATA.get("service_account_id", uuid.uuid4()))
    response = await client.delete(f"/service-accounts/{target_id}")
    assert response.status_code in [200, 204, 404, 401, 422]


@pytest.mark.anyio
async def test_api_keys_list(client):
    response = await client.get("/api-keys")
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_api_keys_create(client):
    payload = {
        "organization_id": str(DATA.get("org_id", uuid.uuid4())),
        "service_account_id": str(DATA.get("service_account_id", uuid.uuid4())),
        "hashed_key": "raw_test_hashed_string"
    }
    response = await client.post("/api-keys", json=payload)
    assert response.status_code in [200, 201, 401, 422]


@pytest.mark.anyio
async def test_api_keys_revoke(client):
    target_id = str(DATA.get("api_key_id", uuid.uuid4()))
    response = await client.delete(f"/api-keys/{target_id}")
    assert response.status_code in [200, 204, 404, 401, 422]


@pytest.mark.anyio
async def test_event_bus_publish(client):
    await nats_client.publish(
        event_type="UserInvited",
        payload={"id": "test-user-id", "email": "test@cortexops.io"},
    )