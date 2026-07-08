-- Create and connect to the identity database
CREATE DATABASE identity;
\c identity;

-- Enable UUID extension (PostgreSQL 13+ has native gen_random_uuid(),
-- but ensuring the extension is loaded is best practice)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- CREATE CUSTOM ENUMS
CREATE TYPE org_status AS ENUM ('ACTIVE', 'SUSPENDED', 'ARCHIVED');
CREATE TYPE org_plan AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
CREATE TYPE user_status AS ENUM ('ACTIVE', 'INVITED', 'DISABLED');

-- PRIMARY TABLES

-- Table: organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status org_status NOT NULL DEFAULT 'ACTIVE',
    plan org_plan NOT NULL DEFAULT 'FREE',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table: users
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

-- Table: roles
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    system_role BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT unique_org_role_name UNIQUE (organization_id, name)
);

-- Table: permissions
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'workflow.execute'
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL
);

-- JOIN TABLES (Many-to-Many Relationships)

-- Table: role_permissions
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Table: user_roles
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- SECURITY TABLES

-- Table: sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_name VARCHAR(255),
    ip_address INET, -- Using native PostgreSQL IP address type
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Table: service_accounts
CREATE TABLE service_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table: api_keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    service_account_id UUID REFERENCES service_accounts(id) ON DELETE CASCADE,
    hashed_key VARCHAR(255) NOT NULL, -- Never store raw keys!
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- PERFORMANCE INDEXES
-- Indexes accelerate foreign key lookups and common querying pathways
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_roles_organization ON roles(organization_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(hashed_key);
CREATE INDEX idx_org_settings_gin ON organizations USING gin(settings); -- Fast JSONB querying