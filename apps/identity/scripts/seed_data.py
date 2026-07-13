import sys
import os
import secrets
from datetime import datetime, timedelta

from apps.identity.domain.api_key import ApiKey
from apps.identity.domain.organization import Organization
from apps.identity.domain.permission import Permission
from apps.identity.domain.role import Role
from apps.identity.domain.service_account import ServiceAccount
from apps.identity.domain.user import User
from apps.identity.infrastructure.database import SessionLocal

# Ensure python can find apps directory from root context
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sqlalchemy.orm import Session
# Replace these imports with the actual locations of your SQLAlchemy models


def seed_database():
    print("🚀 Starting database seeding for identity_db...")
    db: Session = SessionLocal()

    try:
        # 1. Seed Organizations (10 records)
        organizations = []
        for i in range(1, 11):
            org = Organization(
                name=f"Enterprise Corp {i}",
                slug=f"enterprise-corp-{i}",
                is_active=True
            )
            db.add(org)
            organizations.append(org)
        db.flush()  # Flush to populate IDs
        print(f"✓ Seeded {len(organizations)} Organizations.")

        # 2. Seed Permissions (10 records)
        scopes = ["read", "write", "delete", "admin", "deploy", "manage", "view", "export", "audit", "configure"]
        permissions = []
        for scope in scopes:
            perm = Permission(
                name=f"identity:{scope}",
                description=f"Allows identity {scope} operations"
            )
            db.add(perm)
            permissions.append(perm)
        db.flush()
        print(f"✓ Seeded {len(permissions)} Permissions.")

        # 3. Seed Roles (10 records)
        role_names = ["SuperAdmin", "OrgAdmin", "PlatformEng", "DevOps", "Developer", "SecurityAuditor",
                      "BillingManager", "ComplianceOfficer", "SupportTier2", "ReadOnly"]
        roles = []
        for name in role_names:
            role = Role(
                name=name,
                description=f"Standard {name} role mapping",
                # If your model has a many-to-many relationship with permissions:
                permissions=permissions[:3] if name != "SuperAdmin" else permissions
            )
            db.add(role)
            roles.append(role)
        db.flush()
        print(f"✓ Seeded {len(roles)} Roles.")

        # 4. Seed Users (10 records)
        users = []
        for i in range(1, 11):
            user = User(
                email=f"user.{i}@enterprisecorp.com",
                username=f"dev_user_{i}",
                first_name=f"First_{i}",
                last_name=f"Last_{i}",
                keycloak_id=f"kclnk-uuid-mocked-value-0000{i}",  # Connects to Keycloak identities
                is_active=True,
                organization_id=organizations[i - 1].id,  # Distributed across orgs
                role_id=roles[i - 1].id
            )
            db.add(user)
            users.append(user)
        db.flush()
        print(f"✓ Seeded {len(users)} Users.")

        # 5. Seed Service Accounts (10 records)
        service_accounts = []
        for i in range(1, 11):
            sa = ServiceAccount(
                client_id=f"sa-client-{1000 + i}",
                name=f"CI-CD Pipeline Bot {i}",
                description=f"Automated service runner account {i}",
                is_active=True,
                organization_id=organizations[i - 1].id
            )
            db.add(sa)
            service_accounts.append(sa)
        db.flush()
        print(f"✓ Seeded {len(service_accounts)} Service Accounts.")

        # 6. Seed API Keys (10 records)
        for i in range(1, 11):
            api_key = ApiKey(
                name=f"Production Access Key {i}",
                prefix=f"cxop_{secrets.token_hex(4)}",
                hashed_key=secrets.token_urlsafe(32),  # Mocked hash representation
                expires_at=datetime.utcnow() + timedelta(days=365),
                is_active=True,
                user_id=users[i - 1].id,
                organization_id=organizations[i - 1].id
            )
            db.add(api_key)

        db.commit()
        print("🎉 Database successfully populated with comprehensive development data!")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed, rolled back changes. Error: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()