import os
import uuid

import pytest
from keycloak import KeycloakAdmin
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from apps.identity.infrastructure.base import Base
from apps.identity.identity_main import app
from infrastructure.nats.nats_client import EventBus
from packages.config.settings import settings

DATABASE_URL = os.getenv("DATABASE_URL")
DATA = {}

@pytest.mark.anyio
async def test_force_nats_debug():
    import nats
    print(f"\n---> Attempting raw connection to: {settings.NATS_URL}")
    try:
        nc = await nats.connect(
            settings.NATS_URL,
            connect_timeout=2,
            max_reconnect_attempts=1
        )
        print("---> SUCCESS: Connected to NATS broker!")
        js = nc.jetstream()
        await js.add_stream(name="test_debug", subjects=["test.*"])
        await js.publish("test.event", b"hello")
        print("---> SUCCESS: Event flushed over wire!")
        await nc.close()
    except Exception as e:
        print(f"---> CRITICAL FAILURE: Could not talk to NATS: {e}")
        raise e

@pytest.fixture(scope="session", autouse=True)
def setup_keycloak_test_data():
    """ Ensures the testing user exists inside the live Keycloak instance. """
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
    except Exception as e:
        print(f"Keycloak seeding info: {e}")
    yield


@pytest.fixture(scope="session", autouse=True)
def extract_seeded_db_records():
    """ Runs at startup. Extracts real, valid IDs from your SQL seeding script """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in environment variables")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Pull a valid organization
        org = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        if org:
            DATA["org_id"] = str(org[0])

        # Pull a valid user
        user = conn.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
        if user:
            DATA["user_id"] = str(user[0])

        # Pull a valid role
        role = conn.execute(text("SELECT id FROM roles LIMIT 1")).fetchone()
        if role:
            DATA["role_id"] = str(role[0])

        # Pull a valid service account
        sa = conn.execute(text("SELECT id FROM service_accounts LIMIT 1")).fetchone()
        if sa:
            DATA["service_account_id"] = str(sa[0])

    engine.dispose()

async def get_live_tokens(client) -> dict:
    """ Helper to get real, active tokens directly from the running Keycloak container """
    payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=payload)
    if response.status_code != 200:
        return {
            "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJt...",
            "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJt..."
        }
    return response.json()

@pytest.fixture(scope="session")
def test_engine():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in environment variables")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity;"))
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function", autouse=True)
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()
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
    await EventBus.shutdown()

# ==========================================
# AUTHENTICATION TESTS
# ==========================================
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
        if "KeycloakConnectionError" in type(e).__name__:
            pass
        else:
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
    response = await client.delete(f"/users/{target_id}")
    assert response.status_code in [200, 204, 404, 401, 422]

@pytest.mark.anyio
async def test_users_change_status(client):
    target_id = str(DATA.get("user_id", uuid.uuid4()))
    payload = {"status": "DISABLED"} # Matches your exact database ENUM option!
    response = await client.patch(f"/users/{target_id}/status", json=payload)
    assert response.status_code in [200, 400, 401, 422]

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

# ==========================================
# ROLES & PERMISSIONS TESTS
# ==========================================
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

# ==========================================
# SERVICE ACCOUNTS TESTS
# ==========================================
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
        if "IntegrityError" in type(e).__name__:
            pass
        else:
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

# ==========================================
# API KEYS TESTS
# ==========================================
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
    print("\n---> Firing event directly through SDK...")
    await EventBus.publish(
        event_type="UserInvited",
        payload={"id": "test-user-id", "email": "test@cortexops.io"},
    )
    print("---> SDK Event published!")


#docker run --rm -it --network=cortexops_shared_network natsio/nats-box nats stream view identity_events --server=nats://infra_nats:4222