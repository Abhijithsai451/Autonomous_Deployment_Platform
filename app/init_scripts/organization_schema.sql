-- Create and connect to the organization database
CREATE DATABASE organization;
\c organization;

-- Create custom enums
CREATE TYPE org_status AS ENUM ('ACTIVE', 'SUSPENDED', 'ARCHIVED');

-- Create tables
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status org_status NOT NULL DEFAULT 'ACTIVE',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    department_type VARCHAR(50) NOT NULL, -- e.g., 'SRE', 'FINANCE'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE org_settings (
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key VARCHAR(50) NOT NULL,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (organization_id, key)
);

-- Indexes for rapid lookups
CREATE INDEX idx_departments_org ON departments(organization_id);