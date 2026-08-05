-- ========================================================
-- DATABASE SETUP
-- ========================================================
CREATE DATABASE identity;

\c identity;

CREATE SCHEMA IF NOT EXISTS identity;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA identity;

-- ========================================================
-- ENUMS
-- ========================================================
CREATE TYPE identity.user_status AS ENUM ('ACTIVE', 'INVITED', 'DISABLED');
CREATE TYPE identity.outbox_status AS ENUM ('PENDING', 'PROCESSING', 'PUBLISHED', 'FAILED');

-- ========================================================
-- TABLES
-- ========================================================

CREATE TABLE identity.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
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

CREATE TABLE identity.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    system_role BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_org_role_name UNIQUE (organization_id, name)
);

CREATE TABLE identity.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL
);

CREATE TABLE identity.role_permissions (
    role_id UUID NOT NULL REFERENCES identity.roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES identity.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE identity.user_roles (
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES identity.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

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

CREATE TABLE identity.service_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    client_id VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE identity.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    service_account_id UUID REFERENCES identity.service_accounts(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    hashed_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS identity.outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status identity.outbox_status NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    error_message TEXT,
    max_retries INT NOT NULL DEFAULT 5,
    last_error TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- ========================================================
-- PERFORMANCE INDEXES
-- ========================================================
CREATE INDEX idx_users_organization ON identity.users(organization_id);
CREATE INDEX idx_users_email ON identity.users(email);
CREATE INDEX idx_users_status ON identity.users(status);
CREATE INDEX idx_roles_organization ON identity.roles(organization_id);
CREATE INDEX idx_sessions_user ON identity.sessions(user_id);
CREATE INDEX idx_service_accounts_organization ON identity.service_accounts(organization_id);
CREATE INDEX idx_api_keys_organization ON identity.api_keys(organization_id);
CREATE INDEX idx_api_keys_hash ON identity.api_keys(hashed_key);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON identity.outbox_events(status);
CREATE INDEX IF NOT EXISTS idx_outbox_event_type ON identity.outbox_events(event_type);
CREATE INDEX IF NOT EXISTS idx_outbox_aggregate ON identity.outbox_events(aggregate_type, aggregate_id);

-- ========================================================
-- SEED DATA
-- ========================================================
BEGIN;

-- SEED TENANT / ORGANIZATION IDS
WITH mock_orgs AS (
    SELECT
        gen_random_uuid() AS id,
        rn
    FROM generate_series(1, 10) AS rn
),

-- SEED USERS
inserted_users_raw AS (
    INSERT INTO identity.users (organization_id, keycloak_user_id, email, display_name, status)
    SELECT id, gen_random_uuid(), 'user.' || rn || '@enterprisecorp.com', 'Developer User ' || rn, 'ACTIVE'::identity.user_status
    FROM mock_orgs
    RETURNING id, organization_id
),
inserted_users AS (
    SELECT id, organization_id, row_number() OVER (ORDER BY id) as rn FROM inserted_users_raw
),

-- SEED ROLES
inserted_roles_raw AS (
    INSERT INTO identity.roles (organization_id, name, description, system_role)
    SELECT orgs.id, r_templates.name, r_templates.description, r_templates.sys_role
    FROM mock_orgs orgs
    CROSS JOIN (VALUES
        ('AdminRole', 'Full administrative access over all resource schemas', true),
        ('DeveloperRole', 'Read-oriented access policies for operations workspaces', false)
    ) AS r_templates(name, description, sys_role)
    RETURNING id, organization_id, name
),
inserted_roles AS (
    SELECT id, organization_id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_roles_raw
),

-- SEED PERMISSIONS
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

-- SEED ROLE_PERMISSIONS
inserted_role_perms AS (
    INSERT INTO identity.role_permissions (role_id, permission_id)
    SELECT r.id, p.id FROM inserted_roles r
    CROSS JOIN inserted_permissions p
    WHERE (r.name = 'AdminRole') OR (r.name = 'DeveloperRole' AND p.name LIKE '%.read')
    RETURNING role_id
),

-- SEED USER_ROLES
inserted_user_roles AS (
    INSERT INTO identity.user_roles (user_id, role_id)
    SELECT u.id, r.id FROM inserted_users u
    JOIN inserted_roles r ON r.organization_id = u.organization_id
    WHERE r.name = 'AdminRole'
    RETURNING user_id
),

-- SEED SESSIONS
inserted_sessions AS (
    INSERT INTO identity.sessions (user_id, device_name, ip_address, user_agent, metadata, expires_at)
    SELECT id, 'Chrome Mac / Dev Instance', '127.0.0.1'::inet, 'Mozilla/5.0 PyTest/Runner', '{"agent": "seed-script"}'::jsonb, NOW() + INTERVAL '24 hours'
    FROM inserted_users
    RETURNING id
),

-- SEED SERVICE_ACCOUNTS
inserted_service_accounts AS (
    INSERT INTO identity.service_accounts (organization_id, client_id, description)
    SELECT id, 'sa-client-id-00' || rn, 'Automated CI/CD account for organization'
    FROM mock_orgs
    RETURNING id, organization_id
)

-- SEED API_KEYS
INSERT INTO identity.api_keys (organization_id, service_account_id, name, hashed_key, expires_at, revoked_at)
SELECT organization_id, id, 'Default CI Key', 'mocked_argon2_or_sha256_hash_value_string_' || row_number() OVER (), NOW() + INTERVAL '365 days', NULL
FROM inserted_service_accounts;

-- SEED OUTBOX USER CREATED EVENTS
INSERT INTO identity.outbox_events (event_type, aggregate_type, aggregate_id, payload, status)
SELECT
    'identity.user.created',
    'USER',
    id,
    jsonb_build_object(
        'email', email,
        'display_name', display_name,
        'organization_id', organization_id,
        'status', status
    ),
    'PENDING'::identity.outbox_status
FROM identity.users
LIMIT 10;

-- SEED OUTBOX ROLE ASSIGNED EVENTS
INSERT INTO identity.outbox_events (event_type, aggregate_type, aggregate_id, payload, status)
SELECT
    'identity.role.assigned',
    'USER_ROLE',
    user_id,
    jsonb_build_object(
        'user_id', user_id,
        'role_id', role_id,
        'assigned_at', NOW()
    ),
    'PENDING'::identity.outbox_status
FROM identity.user_roles
LIMIT 10;

COMMIT;