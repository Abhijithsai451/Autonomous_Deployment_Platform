--  Create and connect to the organization database
CREATE DATABASE organization;
\c organization;

-- Create custom enums
CREATE TYPE org_status AS ENUM ('ACTIVE', 'SUSPENDED', 'ARCHIVED');
CREATE TYPE org_plan AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
CREATE TYPE dept_type AS ENUM ('SRE', 'SUPPORT', 'FINANCE', 'ENGINEERING', 'OPERATIONS');

-- Create tables
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status org_status NOT NULL DEFAULT 'ACTIVE',
    plan org_plan NOT NULL DEFAULT 'FREE',
    general_settings JSON NOT NULL DEFAULT '{}'::json,
    security_settings JSON NOT NULL DEFAULT '{}'::json,
    llm_settings JSON NOT NULL DEFAULT '{}'::json,
    notification_settings JSON NOT NULL DEFAULT '{}'::json,
    billing_settings JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    lifecycle VARCHAR(100),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type dept_type NOT NULL,
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast microservice lookups
CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_departments_org ON departments(organization_id);