-- ========================================================
-- DATABASE SETUP
-- ========================================================
CREATE DATABASE organization;
\c organization;


CREATE SCHEMA IF NOT EXISTS organization;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA organization;

-- ========================================================
-- ENUMS
-- ========================================================
CREATE TYPE organization.org_status AS ENUM ('ACTIVE', 'SUSPENDED','ARCHIVED')
CREATE TYPE organization.org_plan AS ENUM ('FREE', 'PRO','ENTERPRISE')
CREATE TYPE organization.department_type AS ENUM ('INTERNAL','EXTERNAL', 'SRE', 'SUPPORT')

CREATE TABLE IF NOT EXISTS organization.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status organization.org_status NOT NULL DEFAULT 'ACTIVE',
    plan organization.org_plan NOT NULL DEFAULT 'FREE',
    general_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    security_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    llm_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    notification_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    billing_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization.projects (
    if UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organization.organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    lifecycle VARCHAR(255) NOT NULL DEFAULT 'ACTIVE',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization.departments (
    if UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organization.organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type organization.department_type NOT NULL DEFAULT 'INTERNAL',
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    create_at TIMESTAMPZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPZ NOT NULL DEFAULT NOW()
);
-- ========================================================
--  PERFORMANCE INDEXES
-- ========================================================

CREATE INDEX IF NOT EXISTS idx_projects_organization_id ON organization.projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_departments_organization_id ON organization.departments(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_lifecycle ON organization.projects(lifecycle);
CREATE INDEX IF NOT EXISTS idx_organizations_general_settings_gin ON organization.organizations(general_settings);
CREATE INDEX IF NOT EXISTS idx_projects_metadata_gin ON organization.projects(metadata);
CREATE INDEX IF NOT EXISTS idx_departments_metadata_gin ON organization.departments(metadata);

-- ========================================================
--  SEED DATA
-- ========================================================
BEGIN;

INSERT INTO organization.organizations (id, name, slug, status, plan, general_settings, security_settings, llm_settings, notification_settings, billing_settings)
VALUES
(
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Acme Global',
    'acme-global',
    'ACTIVE',
    'ENTERPRISE',
    '{"timezone": "America/New_York", "language": "en"}'::jsonb,
    '{"mfa_required": true, "ip_whitelist": ["192.168.1.1", "10.0.0.1"]}',
    '{"model": "gpt-4o", "temperature": 0.7, "max_tokens": 2048}',
    '{"email": true, "slack": true, "sms": false}',
    '{"currency": "USD", "payment_method": "wire", "billing_email": "finance@acme.com"}'
),
(
    'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e',
    'Stark Industries',
    'stark-industries',
    'ACTIVE',
    'PRO',
    '{"timezone": "Europe/London", "language": "en"}'::jsonb,
    '{"mfa_required": true, "ip_whitelist": []}',
    '{"model": "claude-3-5-sonnet", "temperature": 0.2, "max_tokens": 4096}',
    '{"email": true, "slack": false, "sms": false}',
    '{"currency": "GBP", "payment_method": "credit_card", "billing_email": "pepper@stark.com"}'
),
(
    'c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f',
    'Wayne Enterprises',
    'wayne-enterprises',
    'SUSPENDED',
    'FREE',
    '{"timezone": "America/Gotham", "language": "en"}'::jsonb,
    '{"mfa_required": false, "ip_whitelist": []}',
    '{"model": "llama-3", "temperature": 0.5, "max_tokens": 1024}',
    '{"email": false, "slack": false, "sms": false}',
    '{"currency": "USD", "payment_method": "none", "billing_email": "alfred@wayne.com"}'
);

-- Seed Projects
INSERT INTO organization.projects (organization_id, name, description, lifecycle, metadata)
VALUES
(
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Project Phoenix',
    'Migration of legacy monolithic systems to cloud-native microservices.',
    'ACTIVE',
    '{"repository": "github.com/acme/phoenix", "lead_engineer": "Alice", "priority": "high"}'::jsonb
),
(
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Project Icarus',
    'Experimental research into edge-computing processing times.',
    'PLANNING',
    '{"repository": "github.com/acme/icarus", "target_quarter": "Q4", "budget_code": "R-D-99"}'::jsonb
),
(
    'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e',
    'Friday AI Expansion',
    'Upgrading internal infrastructure for localized LLM instances.',
    'ACTIVE',
    '{"repository": "gitlab.stark.internal/friday", "compute_cluster": "JARVIS-04"}'::jsonb
);

-- Seed Departments
INSERT INTO organization.departments (organization_id, name, type, description, metadata)
VALUES
(
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Core Reliability Engineering',
    'SRE',
    'Responsible for uptime, infrastructure provisioning, and CI/CD pipelines.',
    '{"cost_center": "CC-401", "headcount_target": 12, "slack_channel": "#eng-sre"}'::jsonb
),
(
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Global Customer Care',
    'SUPPORT',
    'Tier 1 to Tier 3 technical support for enterprise contract holders.',
    '{"cost_center": "CC-902", "coverage": "24/7/365", "system": "Zendesk"}'::jsonb
),
(
    'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e',
    'Advanced Weapons Division',
    'INTERNAL',
    'Internal design group focusing on clean energy defense systems.',
    '{"clearance_level": "Level 5", "location": "Malibu Lab"}'::jsonb
);
