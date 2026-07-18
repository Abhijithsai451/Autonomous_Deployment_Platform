CREATE DATABASE identity;
\c identity;

-- Create the dedicated schema
CREATE SCHEMA IF NOT EXISTS identity;
SET search_path TO identity;

-- Enable UUID extension inside this database context
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- CREATE CUSTOM ENUMS (Now safely locked inside the identity schema)
CREATE TYPE org_status AS ENUM ('ACTIVE', 'SUSPENDED', 'ARCHIVED');
CREATE TYPE org_plan AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
CREATE TYPE user_status AS ENUM ('ACTIVE', 'INVITED', 'DISABLED');

-- PRIMARY TABLES
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status org_status NOT NULL DEFAULT 'ACTIVE',
    plan org_plan NOT NULL DEFAULT 'FREE',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    keycloak_user_id UUID UNIQUE NOT NULL,
    email VARCHAR(320) NOT NULL,
    display_name VARCHAR(255),
    status user_status NOT NULL DEFAULT 'INVITED',
    timezone VARCHAR(100) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    system_role BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT unique_org_role_name UNIQUE (organization_id, name)
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL
);

-- JOIN TABLES
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- SECURITY TABLES
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_name VARCHAR(255),
    ip_address INET,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE service_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    service_account_id UUID REFERENCES service_accounts(id) ON DELETE CASCADE,
    hashed_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- PERFORMANCE INDEXES
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_roles_organization ON roles(organization_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(hashed_key);
CREATE INDEX idx_org_settings_gin ON organizations USING gin(settings);

-- Force session state context before seeding
\c identity;
SET search_path TO identity;

BEGIN;

-- 1. SEED ORGANIZATIONS
WITH inserted_orgs_raw AS (
    INSERT INTO organizations (name, slug, status, plan, settings) VALUES
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
    INSERT INTO users (organization_id, keycloak_user_id, email, display_name, status)
    SELECT id, gen_random_uuid(), 'user.' || rn || '@enterprisecorp.com', 'Developer User ' || rn, 'ACTIVE'::user_status
    FROM inserted_orgs
    RETURNING id, organization_id
),
inserted_users AS (
    SELECT id, organization_id, row_number() OVER (ORDER BY id) as rn FROM inserted_users_raw
),

-- 3. SEED ROLES
inserted_roles_raw AS (
    INSERT INTO roles (organization_id, name, system_role)
    SELECT orgs.id, r_templates.name, r_templates.sys_role
    FROM inserted_orgs orgs
    CROSS JOIN (VALUES ('AdminRole', true), ('DeveloperRole', false)) AS r_templates(name, sys_role)
    RETURNING id, organization_id, name
),
inserted_roles AS (
    SELECT id, organization_id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_roles_raw
),

-- 4. SEED PERMISSIONS
inserted_permissions_raw AS (
    INSERT INTO permissions (name, resource, action) VALUES
    ('identity.read', 'identity', 'read'),
    ('identity.write', 'identity', 'write'),
    ('workflow.execute', 'workflow', 'execute'),
    ('workflow.read', 'workflow', 'read'),
    ('org.manage', 'organization', 'manage'),
    ('org.view', 'organization', 'view'),
    ('billing.manage', 'billing', 'manage'),
    ('audit.view', 'audit', 'view'),
    ('secrets.manage', 'secrets', 'manage'),
    ('secrets.read', 'secrets', 'read')
    RETURNING id, name
),
inserted_permissions AS (
    SELECT id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_permissions_raw
),

-- 5. SEED ROLE_PERMISSIONS
inserted_role_perms AS (
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT r.id, p.id FROM inserted_roles r
    CROSS JOIN inserted_permissions p
    WHERE (r.name = 'AdminRole') OR (r.name = 'DeveloperRole' AND p.name LIKE '%.read')
    RETURNING role_id
),

-- 6. SEED USER_ROLES
inserted_user_roles AS (
    INSERT INTO user_roles (user_id, role_id)
    SELECT u.id, r.id FROM inserted_users u
    JOIN inserted_roles r ON r.organization_id = u.organization_id
    WHERE r.name = 'AdminRole'
    RETURNING user_id
),

-- 7. SEED SESSIONS
inserted_sessions AS (
    INSERT INTO sessions (user_id, device_name, ip_address, metadata, expires_at)
    SELECT id, 'Chrome Mac / Dev Instance', '127.0.0.1'::inet, '{"agent": "seed-script"}'::jsonb, NOW() + INTERVAL '24 hours'
    FROM inserted_users
    RETURNING id
),

-- 8. SEED SERVICE_ACCOUNTS
inserted_service_accounts AS (
    INSERT INTO service_accounts (organization_id, client_id, description)
    SELECT id, 'sa-client-id-00' || rn, 'Automated CI/CD account for organization'
    FROM inserted_orgs
    RETURNING id, organization_id
)

-- 9. SEED API_KEYS
INSERT INTO api_keys (organization_id, service_account_id, hashed_key, expires_at)
SELECT organization_id, id, 'mocked_argon2_or_sha256_hash_value_string_' || row_number() OVER (), NOW() + INTERVAL '365 days'
FROM inserted_service_accounts;

COMMIT;