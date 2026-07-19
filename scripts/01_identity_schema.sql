-- 1. Provision the independent database peer next to cortexops
CREATE DATABASE identity;

-- 2. Explicitly switch context to the new database
\c identity;

-- 3. Create the isolated schema namespace
CREATE SCHEMA IF NOT EXISTS identity;

-- 4. Enable extensions directly inside the schema context
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA identity;

-- ========================================================
-- 👑 ENUMS (Explicitly bound to the identity schema namespace)
-- ========================================================
CREATE TYPE identity.org_status AS ENUM ('ACTIVE', 'SUSPENDED', 'ARCHIVED');
CREATE TYPE identity.org_plan AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
CREATE TYPE identity.user_status AS ENUM ('ACTIVE', 'INVITED', 'DISABLED');

-- ========================================================
-- 📊 TABLES (Explicitly created inside identity schema)
-- ========================================================

-- Table: organizations
CREATE TABLE identity.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status identity.org_status NOT NULL DEFAULT 'ACTIVE',
    plan identity.org_plan NOT NULL DEFAULT 'FREE',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table: users
CREATE TABLE identity.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES identity.organizations(id) ON DELETE CASCADE,
    keycloak_user_id UUID UNIQUE NOT NULL,
    email VARCHAR(320) NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    status identity.user_status NOT NULL DEFAULT 'INVITED',
    timezone VARCHAR(64) DEFAULT 'UTC',
    locale VARCHAR(16) DEFAULT 'en',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_org_user_email UNIQUE (organization_id, email)
);

-- Table: roles
CREATE TABLE identity.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES identity.organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    system_role BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_org_role_name UNIQUE (organization_id, name)
);

-- Table: permissions
CREATE TABLE identity.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL
);

-- Table: role_permissions
CREATE TABLE identity.role_permissions (
    role_id UUID NOT NULL REFERENCES identity.roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES identity.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Table: user_roles
CREATE TABLE identity.user_roles (
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES identity.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Table: sessions
CREATE TABLE identity.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    device_name VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

-- Table: service_accounts
CREATE TABLE identity.service_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES identity.organizations(id) ON DELETE CASCADE,
    client_id VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table: api_keys
CREATE TABLE identity.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES identity.organizations(id) ON DELETE CASCADE,
    service_account_id UUID REFERENCES identity.service_accounts(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    hashed_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

-- PERFORMANCE INDEXES
CREATE INDEX idx_users_organization ON identity.users(organization_id);
CREATE INDEX idx_users_email ON identity.users(email);
CREATE INDEX idx_users_status ON identity.users(status);
CREATE INDEX idx_organizations_status ON identity.organizations(status);
CREATE INDEX idx_roles_organization ON identity.roles(organization_id);
CREATE INDEX idx_sessions_user ON identity.sessions(user_id);
CREATE INDEX idx_api_keys_hash ON identity.api_keys(hashed_key);
CREATE INDEX idx_org_settings_gin ON identity.organizations USING gin(settings);

-- ========================================================
-- 🌱 SEED DATA DATASEED BLOCK
-- ========================================================
BEGIN;

-- 1. SEED ORGANIZATIONS
WITH inserted_orgs_raw AS (
    INSERT INTO identity.organizations (name, slug, status, plan, settings) VALUES
    ('Enterprise Corp 1', 'enterprise-corp-1', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 2', 'enterprise-corp-2', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 3', 'enterprise-corp-3', 'ACTIVE', 'PRO', '{}'),
    ('Enterprise Corp 4', 'enterprise-corp-4', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 5', 'enterprise-corp-5', 'ACTIVE', 'ENTERPRISE', '{}'),
    ('Enterprise Corp 6', 'enterprise-corp-6', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 7', 'enterprise-corp-7', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 8', 'enterprise-corp-8', 'ACTIVE', 'PRO', '{}'),
    ('Enterprise Corp 9', 'enterprise-corp-9', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 10', 'enterprise-corp-10', 'ACTIVE', 'ENTERPRISE', '{}')
    RETURNING id
),
inserted_orgs AS (
    SELECT id, row_number() OVER (ORDER BY id) as rn FROM inserted_orgs_raw
),

-- 2. SEED USERS
inserted_users_raw AS (
    INSERT INTO identity.users (organization_id, keycloak_user_id, email, display_name, status)
    SELECT id, gen_random_uuid(), 'user.' || rn || '@enterprisecorp.com', 'Developer User ' || rn, 'ACTIVE'::identity.user_status
    FROM inserted_orgs
    RETURNING id, organization_id
),
inserted_users AS (
    SELECT id, organization_id, row_number() OVER (ORDER BY id) as rn FROM inserted_users_raw
),

-- 3. SEED ROLES (Populating planned description field)
inserted_roles_raw AS (
    INSERT INTO identity.roles (organization_id, name, description, system_role)
    SELECT orgs.id, r_templates.name, r_templates.description, r_templates.sys_role
    FROM inserted_orgs orgs
    CROSS JOIN (VALUES
        ('AdminRole', 'Full administrative access over all resource schemas', true),
        ('DeveloperRole', 'Read-oriented access policies for operations workspaces', false)
    ) AS r_templates(name, description, sys_role)
    RETURNING id, organization_id, name
),
inserted_roles AS (
    SELECT id, organization_id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_roles_raw
),

-- 4. SEED PERMISSIONS (Populating planned description field)
inserted_permissions_raw AS (
    INSERT INTO identity.permissions (name, description, resource, action) VALUES
    ('identity.read', 'Allows reading identities, groups, and scopes', 'identity', 'read'),
    ('identity.write', 'Allows modifying user registry structures', 'identity', 'write'),
    ('workflow.execute', 'Allows launching active container operations', 'workflow', 'execute'),
    ('workflow.read', 'Allows parsing log strings from executions', 'workflow', 'read'),
    ('org.manage', 'Complete layout modifications on organization namespaces', 'organization', 'manage'),
    ('org.view', 'Lookup status matrices across the organization footprint', 'organization', 'view'),
    ('billing.manage', 'Update active banking credentials and payment schemas', 'billing', 'manage'),
    ('audit.view', 'Access compliance-ready system ledger footprints', 'audit', 'view'),
    ('secrets.manage', 'Mutate cryptographic entries and sensitive configurations', 'secrets', 'manage'),
    ('secrets.read', 'Retrieve decryption vectors for runtime dependencies', 'secrets', 'read')
    RETURNING id, name
),
inserted_permissions AS (
    SELECT id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_permissions_raw
),

-- 5. SEED ROLE_PERMISSIONS
inserted_role_perms AS (
    INSERT INTO identity.role_permissions (role_id, permission_id)
    SELECT r.id, p.id FROM inserted_roles r
    CROSS JOIN inserted_permissions p
    WHERE (r.name = 'AdminRole') OR (r.name = 'DeveloperRole' AND p.name LIKE '%.read')
    RETURNING role_id
),

-- 6. SEED USER_ROLES
inserted_user_roles AS (
    INSERT INTO identity.user_roles (user_id, role_id)
    SELECT u.id, r.id FROM inserted_users u
    JOIN inserted_roles r ON r.organization_id = u.organization_id
    WHERE r.name = 'AdminRole'
    RETURNING user_id
),

-- 7. SEED SESSIONS
inserted_sessions AS (
    INSERT INTO identity.sessions (user_id, device_name, ip_address, user_agent, metadata, expires_at)
    SELECT id, 'Chrome Mac / Dev Instance', '127.0.0.1'::inet, 'Mozilla/5.0 PyTest/Runner', '{"agent": "seed-script"}'::jsonb, NOW() + INTERVAL '24 hours'
    FROM inserted_users
    RETURNING id
),

-- 8. SEED SERVICE_ACCOUNTS
inserted_service_accounts AS (
    INSERT INTO identity.service_accounts (organization_id, client_id, description)
    SELECT id, 'sa-client-id-00' || rn, 'Automated CI/CD account for organization'
    FROM inserted_orgs
    RETURNING id, organization_id
)

-- 9. SEED API_KEYS (Populating planned name and revoked_at properties cleanly)
INSERT INTO identity.api_keys (organization_id, service_account_id, name, hashed_key, expires_at, revoked_at)
SELECT organization_id, id, 'Default CI Key', 'mocked_argon2_or_sha256_hash_value_string_' || row_number() OVER (), NOW() + INTERVAL '365 days', NULL
FROM inserted_service_accounts;

COMMIT;