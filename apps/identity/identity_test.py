import os
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from apps.identity.infrastructure.base import Base
from apps.identity.identity_main import app
from apps.identity.domain.user import User
from apps.identity.domain.role import Role
from apps.identity.domain.permission import Permission
from apps.identity.domain.api_key import ApiKey
from apps.identity.domain.service_account import ServiceAccount
from apps.identity.infrastructure.keycloak_client import KeycloakClient

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture(scope="session", autouse=True)
def setup_keycloak_test_data():
    """
    Runs once before the test suite. Ensures a testing realm, client,
    and testing user exist directly in the real Keycloak instance.
    """
    keycloak_client = KeycloakClient()
    target_realm = os.getenv("KEYCLOAK_REALM", "cortexops")
    test_user = {
            "email": "testuser@cortexops.io",
            "username": "testuser",
            "enabled": True,
            "credentials": [{"value": "secure_password", "type": "password", "temporary": False}]
        }
    try:

        keycloak_client.admin.create_user(test_user, exist_ok=True)
        print("\n✅ Successfully seeded 'testuser' in Keycloak!")
    except Exception as e:
        print(f"Keycloak test user status: {e}")

    yield

async def get_fresh_tokens(client) -> dict:
    login_payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=login_payload)
    if response.status_code != 200:
        raise RuntimeError(f"Setup failed: Could not log in test user. Response: {response.text}")
    return response.json()

@pytest.fixture(scope="session")
def test_engine():
    """
    Creates the single database engine connected to the PostgreSQL database
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in .env")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity;"))
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function", autouse=True)
def db_session(test_engine):
    """
    Provides a transactional session. Everything written to the database
    during a test is automatically rolled back when the test finishes.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        autocommit = False,
        autoflush = False,
        bind = connection
    )
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


# Authentication
@pytest.mark.anyio
async def test_auth_login(client):
    """Test standard user login using real Keycloak credentials."""
    payload = {"username": "testuser", "password": "secure_password"}
    response = await client.post("/auth/login", data=payload)

    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

@pytest.mark.anyio
async def test_auth_refresh(client):
    """Test token refresh using a real, active refresh token."""
    tokens = await get_fresh_tokens(client)
    refresh_token = tokens["refresh_token"]

    payload = {"refresh_token": refresh_token}
    response = await client.post("/auth/refresh", json=payload)

    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

@pytest.mark.anyio
async def test_auth_logout(client):
    """Test session termination using a real, active refresh token."""
    # 1. Dynamically get a real token
    tokens = await get_fresh_tokens(client)
    refresh_token = tokens["refresh_token"]

    # 2. Perform the logout test
    payload = {"refresh_token": refresh_token}
    response = await client.post("/auth/logout", json=payload)

    assert response.status_code in [200, 204]

@pytest.mark.anyio
async def test_auth_me(client):
    response = await client.get("/auth/me")
    assert response.status_code in [200, 401]

# 2. USERS ROUTE TESTS

@pytest.mark.anyio
async def test_users_invite(client):
    payload = {"email": "newuser@cortexops.io",
               "role_id": "admin-role",
               "organization_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
               "display_name": "New User"
               }
    response = await client.post("/users/invite", json=payload)
    print("\n Invite Error Details: ", response.json())
    assert response.status_code in [200, 201]

@pytest.mark.anyio
async def test_users_list(client):
    response = await client.get("/users")
    assert response.status_code in [200, 401]

@pytest.mark.anyio
async def test_users_get_by_id(client):
    response = await client.get("/users/some-uuid-123")
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_users_patch(client):
    payload = {"username": "updated_name"}
    response = await client.patch("/users/some-uuid-123", json=payload)
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_users_delete(client):
    response = await client.delete("/users/some-uuid-123")
    assert response.status_code in [200, 204, 404, 401]

@pytest.mark.anyio
async def test_users_change_status(client):
    payload = {"status": "SUSPENDED"}
    response = await client.patch("/users/some-uuid-123/status", json=payload)
    assert response.status_code in [200, 400, 401]

@pytest.mark.anyio
async def test_users_assign_role(client):
    payload = {"role_id": "role-uuid-abc"}
    response = await client.post("/users/some-uuid-123/roles", json=payload)
    assert response.status_code in [200, 201, 404, 401]

@pytest.mark.anyio
async def test_users_remove_role(client):
    response = await client.delete("/users/some-uuid-123/roles/role-uuid-abc")
    assert response.status_code in [200, 204, 404, 401]


# 3. ROLES & PERMISSIONS ROUTE TESTS

@pytest.mark.anyio
async def test_roles_get(client):
    response = await client.get("/roles")
    assert response.status_code in [200, 401]

@pytest.mark.anyio
async def test_roles_create(client):
    payload = {"name": "Editor", "permissions": ["read", "write"]}
    response = await client.post("/roles", json=payload)
    assert response.status_code in [200, 201, 400, 401]

@pytest.mark.anyio
async def test_roles_patch(client):
    payload = {"description": "Updated Role description"}
    response = await client.patch("/roles/role-uuid-abc", json=payload)
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_roles_delete(client):
    response = await client.delete("/roles/role-uuid-abc")
    assert response.status_code in [200, 204, 404, 401]

@pytest.mark.anyio
async def test_permissions_get(client):
    response = await client.get("/permissions")
    assert response.status_code in [200, 401]


# 4. SERVICE ACCOUNTS ROUTE TESTS

@pytest.mark.anyio
async def test_service_accounts_list(client):
    response = await client.get("/service-accounts")
    assert response.status_code in [200, 401]

@pytest.mark.anyio
async def test_service_accounts_create(client):
    payload = {"name": "Deployment-Runner", "description": "CI/CD Agent"}
    response = await client.post("/service-accounts", json=payload)
    assert response.status_code in [200, 201, 401]

@pytest.mark.anyio
async def test_service_accounts_patch(client):
    payload = {"description": "Updated deployment account details"}
    response = await client.patch("/service-accounts/sa-uuid-xyz", json=payload)
    assert response.status_code in [200, 404, 401]

@pytest.mark.anyio
async def test_service_accounts_delete(client):
    response = await client.delete("/service-accounts/sa-uuid-xyz")
    assert response.status_code in [200, 204, 404, 401]


# 5. API KEYS ROUTE TESTS

@pytest.mark.anyio
async def test_api_keys_list(client):
    response = await client.get("/api-keys")
    assert response.status_code in [200, 401]

@pytest.mark.anyio
async def test_api_keys_create(client):
    payload = {"name": "Production-Secret-Key", "expires_in_days": 30}
    response = await client.post("/api-keys", json=payload)
    assert response.status_code in [200, 201, 401]

@pytest.mark.anyio
async def test_api_keys_revoke(client):
    # Triggers DELETE /api-keys/{id} (Revoke Key)
    response = await client.delete("/api-keys/key-uuid-999")
    assert response.status_code in [200, 204, 404, 401]


