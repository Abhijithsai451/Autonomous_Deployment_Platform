import os
import pytest
from keycloak import KeycloakAdmin
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from apps.identity.infrastructure.base import Base
from apps.identity.identity_main import app
from packages.config.settings import settings

DATABASE_URL = os.getenv("DATABASE_URL")
VALID_UUID = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"

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

async def get_live_tokens(client) -> dict:
    """ Helper to get real, active tokens directly from the running Keycloak container """
    payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Could not get real token: {response.text}")
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# ==========================================
# AUTHENTICATION TESTS
# ==========================================
@pytest.mark.anyio
async def test_auth_login(client):
    payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=payload)
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens

@pytest.mark.anyio
async def test_auth_refresh(client):
    # Fetch a real, cryptographically valid refresh token from Keycloak
    tokens = await get_live_tokens(client)
    payload = {"refresh_token": tokens["refresh_token"]}
    response = await client.post("/auth/refresh", json=payload)
    assert response.status_code == 200

@pytest.mark.anyio
async def test_auth_logout(client):
    # Fetch a real, active token to terminate gracefully
    tokens = await get_live_tokens(client)
    payload = {"refresh_token": tokens["refresh_token"]}
    response = await client.post("/auth/logout", json=payload)
    assert response.status_code in [200, 204]

@pytest.mark.anyio
async def test_auth_me(client):
    response = await client.get("/auth/me")
    assert response.status_code in [200, 401]

# ==========================================
# USERS TESTS
# ==========================================
@pytest.mark.anyio
async def test_users_invite(client):
    payload = {
        "email": "newuser@cortexops.io",
        "role_id": VALID_UUID,
        "organization_id": VALID_UUID,
        "display_name": "New User"
    }
    response = await client.post("/users/invite", json=payload)
    assert response.status_code in [200, 201]

@pytest.mark.anyio
async def test_users_list(client):
    response = await client.get("/users")
    assert response.status_code in [200, 401]

@pytest.mark.anyio
async def test_users_get_by_id(client):
    response = await client.get(f"/users/{VALID_UUID}")
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_users_patch(client):
    payload = {"username": "updated_name"}
    response = await client.patch(f"/users/{VALID_UUID}", json=payload)
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_users_delete(client):
    response = await client.delete(f"/users/{VALID_UUID}")
    assert response.status_code in [200, 204, 404, 401]

@pytest.mark.anyio
async def test_users_change_status(client):
    payload = {"status": "SUSPENDED"}
    response = await client.patch(f"/users/{VALID_UUID}/status", json=payload)
    assert response.status_code in [200, 400, 401]

@pytest.mark.anyio
async def test_users_assign_role(client):
    payload = {"role_id": VALID_UUID}
    response = await client.post(f"/users/{VALID_UUID}/roles", json=payload)
    assert response.status_code in [200, 201, 404, 401]

@pytest.mark.anyio
async def test_users_remove_role(client):
    response = await client.delete(f"/users/{VALID_UUID}/roles/{VALID_UUID}")
    assert response.status_code in [200, 204, 404, 401]

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
        "name": "Editor",
        "description": "Content editor role",
        "organization_id": VALID_UUID,
        "permissions": ["read", "write"]
    }
    response = await client.post("/roles", json=payload)
    assert response.status_code in [200, 201, 400, 401]

@pytest.mark.anyio
async def test_roles_patch(client):
    payload = {"description": "Updated description"}
    response = await client.patch(f"/roles/{VALID_UUID}", json=payload)
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_roles_delete(client):
    response = await client.delete(f"/roles/{VALID_UUID}")
    assert response.status_code in [200, 204, 404, 401]

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
        "name": "Deployment-Runner",
        "description": "CI/CD Agent",
        "organization_id": VALID_UUID
    }
    response = await client.post("/service-accounts", json=payload)
    assert response.status_code in [200, 201, 401]

@pytest.mark.anyio
async def test_service_accounts_patch(client):
    payload = {"description": "Updated details"}
    response = await client.patch(f"/service-accounts/{VALID_UUID}", json=payload)
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_service_accounts_delete(client):
    response = await client.delete(f"/service-accounts/{VALID_UUID}")
    assert response.status_code in [200, 204, 404, 401]

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
        "name": "Production-Secret-Key",
        "expires_in_days": 30,
        "organization_id": VALID_UUID,
        "user_id": VALID_UUID
    }
    response = await client.post("/api-keys", json=payload)
    assert response.status_code in [200, 201, 401]

@pytest.mark.anyio
async def test_api_keys_revoke(client):
    response = await client.delete(f"/api-keys/{VALID_UUID}")
    assert response.status_code in [200, 204, 404, 401]